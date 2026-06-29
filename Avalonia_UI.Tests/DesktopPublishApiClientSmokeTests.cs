using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Runtime.Loader;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class DesktopPublishApiClientSmokeTests
{
    [TestMethod]
    public async Task PublishedDesktopApiClientConnectsToPortableEngineHost()
    {
        var repoRoot = FindRepoRoot();
        var pythonExe = RepoPythonExe(repoRoot);
        var portableRoot = Path.Combine(
            repoRoot,
            ".tmp",
            $"FlowWeaverPortableDesktopPublishApi-{Guid.NewGuid():N}");
        RunCommand(
            pythonExe,
            new[]
            {
                "tools\\create_portable_layout.py",
                "--output",
                portableRoot,
                "--no-desktop-build",
            },
            repoRoot);
        RunCommand(
            pythonExe,
            new[]
            {
                "tools\\publish_desktop.py",
                "--output",
                Path.Combine(portableRoot, "Desktop"),
            },
            repoRoot);

        var engineHostDir = Path.Combine(portableRoot, "EngineHost");
        var desktopDir = Path.Combine(portableRoot, "Desktop");
        var publishedAssemblyPath = Path.Combine(desktopDir, "Avalonia_UI.dll");
        Assert.IsTrue(File.Exists(Path.Combine(desktopDir, "Avalonia_UI.exe")));
        Assert.IsTrue(File.Exists(publishedAssemblyPath));

        var port = FreePort();
        var process = StartPortableEngineHost(engineHostDir, port);
        try
        {
            var loadContext = new PublishedDesktopLoadContext(publishedAssemblyPath);
            try
            {
                var assembly = loadContext.LoadFromAssemblyPath(publishedAssemblyPath);
                var client = Activator.CreateInstance(
                    RequiredType(assembly, "Avalonia_UI.Api.EngineHostApiClient"))!;
                var baseUrl = $"http://127.0.0.1:{port}";

                var healthSettings = CreateConnectionSettings(assembly, baseUrl);
                var healthEnvelope = await WaitForPublishedHealthAsync(
                    client,
                    healthSettings,
                    process);
                AssertEnvelopeOk(healthEnvelope);
                Assert.AreEqual(
                    "ok",
                    Property<string>(
                        Property<object>(healthEnvelope, "Data"),
                        "Status"));

                var token = File.ReadAllText(
                    Path.Combine(
                        engineHostDir,
                        "runtime",
                        "config",
                        "local_api_token"))
                    .Trim();
                Assert.IsFalse(string.IsNullOrWhiteSpace(token));
                var settings = CreateConnectionSettings(assembly, baseUrl, token);

                var nodeDefinitionsEnvelope = await InvokeApiAsync(
                    client,
                    "ListNodeDefinitionsAsync",
                    settings,
                    CancellationToken.None);
                AssertEnvelopeOk(nodeDefinitionsEnvelope);
                var nodeTypes = EnumerableFromEnvelope(nodeDefinitionsEnvelope)
                    .Select(item => Property<string>(item, "NodeType"))
                    .ToArray();
                CollectionAssert.IsSubsetOf(
                    new[]
                    {
                        "GenerateTestTableNode",
                        "FilterRowsNode",
                        "PublishSharedTablesNode",
                    },
                    nodeTypes);

                var workflowsEnvelope = await InvokeApiAsync(
                    client,
                    "ListWorkflowsAsync",
                    settings,
                    CancellationToken.None);
                AssertEnvelopeOk(workflowsEnvelope);
                Assert.AreEqual(0, EnumerableFromEnvelope(workflowsEnvelope).Count());
            }
            finally
            {
                loadContext.Unload();
            }
        }
        finally
        {
            StopProcess(process);
            TryDeleteDirectory(portableRoot);
        }
    }

    private static object CreateConnectionSettings(
        Assembly assembly,
        string baseUrl,
        string? token = null)
    {
        var settingsType = RequiredType(
            assembly,
            "Avalonia_UI.Models.EngineHostConnectionSettings");
        var settings = Activator.CreateInstance(settingsType)!;
        settingsType.GetProperty("BaseUrl")!.SetValue(settings, baseUrl);
        if (token is not null)
        {
            settingsType.GetProperty("Token")!.SetValue(settings, token);
        }

        return settings;
    }

    private static async Task<object> InvokeApiAsync(
        object client,
        string methodName,
        params object?[] args)
    {
        var method = client.GetType()
            .GetMethods()
            .Single(item =>
                item.Name == methodName
                && item.GetParameters().Length == args.Length);
        var task = (Task)method.Invoke(client, args)!;
        await task.ConfigureAwait(false);
        return task.GetType().GetProperty("Result")!.GetValue(task)!;
    }

    private static async Task<object> WaitForPublishedHealthAsync(
        object client,
        object settings,
        EngineHostProcess process)
    {
        var deadline = DateTimeOffset.UtcNow.AddSeconds(20);
        object? lastEnvelope = null;
        while (DateTimeOffset.UtcNow < deadline)
        {
            AssertProcessRunning(process);
            lastEnvelope = await InvokeApiAsync(
                client,
                "GetHealthAsync",
                settings,
                CancellationToken.None);
            if (Property<bool>(lastEnvelope, "Ok")
                && Property<object?>(lastEnvelope, "Data") is not null)
            {
                return lastEnvelope;
            }

            await Task.Delay(100);
        }

        Assert.Fail(
            "EngineHost health did not become ok. "
            + $"Last envelope: {lastEnvelope}. "
            + $"stderr: {process.StderrTail()}");
        throw new UnreachableException();
    }

    private static void AssertEnvelopeOk(object envelope)
    {
        Assert.IsTrue(
            Property<bool>(envelope, "Ok"),
            Property<object?>(envelope, "Error")?.ToString());
        Assert.IsNotNull(Property<object?>(envelope, "Data"));
    }

    private static IEnumerable<object> EnumerableFromEnvelope(object envelope)
    {
        return ((IEnumerable)Property<object>(envelope, "Data")).Cast<object>();
    }

    private static T Property<T>(object instance, string name)
    {
        return (T)instance.GetType().GetProperty(name)!.GetValue(instance)!;
    }

    private static Type RequiredType(Assembly assembly, string typeName)
    {
        return assembly.GetType(typeName, throwOnError: true)!;
    }

    private static EngineHostProcess StartPortableEngineHost(
        string engineHostDir,
        int port)
    {
        var pythonExe = Path.Combine(engineHostDir, "python312", "python.exe");
        var startInfo = new ProcessStartInfo
        {
            FileName = pythonExe,
            WorkingDirectory = engineHostDir,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
        startInfo.Environment.Remove("PYTHONPATH");
        startInfo.ArgumentList.Add("-m");
        startInfo.ArgumentList.Add("uvicorn");
        startInfo.ArgumentList.Add("--app-dir");
        startInfo.ArgumentList.Add(Path.Combine(engineHostDir, "src"));
        startInfo.ArgumentList.Add("flowweaver.api.app:create_default_app");
        startInfo.ArgumentList.Add("--factory");
        startInfo.ArgumentList.Add("--host");
        startInfo.ArgumentList.Add("127.0.0.1");
        startInfo.ArgumentList.Add("--port");
        startInfo.ArgumentList.Add(port.ToString());

        var process = new Process { StartInfo = startInfo };
        var stdout = new StringBuilder();
        var stderr = new StringBuilder();
        process.OutputDataReceived += (_, args) => AppendLine(stdout, args.Data);
        process.ErrorDataReceived += (_, args) => AppendLine(stderr, args.Data);
        Assert.IsTrue(process.Start());
        process.BeginOutputReadLine();
        process.BeginErrorReadLine();
        return new EngineHostProcess(process, stdout, stderr);
    }

    private static void RunCommand(
        string fileName,
        string[] arguments,
        string workingDirectory)
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = fileName,
            WorkingDirectory = workingDirectory,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
        foreach (var argument in arguments)
        {
            startInfo.ArgumentList.Add(argument);
        }

        var process = Process.Start(startInfo);
        Assert.IsNotNull(process);
        Assert.IsTrue(
            process!.WaitForExit(240_000),
            $"{fileName} did not exit in time.");
        var stdout = process.StandardOutput.ReadToEnd();
        var stderr = process.StandardError.ReadToEnd();
        Assert.AreEqual(
            0,
            process.ExitCode,
            $"{fileName} failed.\nstdout:\n{stdout}\nstderr:\n{stderr}");
    }

    private static void StopProcess(EngineHostProcess engineHost)
    {
        var process = engineHost.Process;
        if (process.HasExited)
        {
            return;
        }

        process.Kill(entireProcessTree: true);
        process.WaitForExit(5000);
    }

    private static void AssertProcessRunning(EngineHostProcess process)
    {
        if (!process.Process.HasExited)
        {
            return;
        }

        Assert.Fail(
            $"EngineHost exited with code {process.Process.ExitCode}. "
            + $"stderr: {process.StderrTail()}");
    }

    private static string FindRepoRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            if (File.Exists(Path.Combine(directory.FullName, "pyproject.toml"))
                && Directory.Exists(Path.Combine(
                    directory.FullName,
                    "Avalonia_UI")))
            {
                return directory.FullName;
            }

            directory = directory.Parent;
        }

        throw new DirectoryNotFoundException(
            "FlowWeaver repository root was not found.");
    }

    private static string RepoPythonExe(string repoRoot)
    {
        var pythonExe = Path.Combine(repoRoot, "python312", "python.exe");
        return File.Exists(pythonExe) ? pythonExe : "python";
    }

    private static void TryDeleteDirectory(string path)
    {
        try
        {
            Directory.Delete(path, recursive: true);
        }
        catch (IOException)
        {
        }
        catch (UnauthorizedAccessException)
        {
        }
    }

    private static int FreePort()
    {
        using var listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        return ((IPEndPoint)listener.LocalEndpoint).Port;
    }

    private static void AppendLine(StringBuilder builder, string? line)
    {
        if (line is null)
        {
            return;
        }

        lock (builder)
        {
            builder.AppendLine(line);
        }
    }

    private sealed class PublishedDesktopLoadContext : AssemblyLoadContext
    {
        private readonly AssemblyDependencyResolver _resolver;

        public PublishedDesktopLoadContext(string mainAssemblyPath)
            : base(isCollectible: true)
        {
            _resolver = new AssemblyDependencyResolver(mainAssemblyPath);
        }

        protected override Assembly? Load(AssemblyName assemblyName)
        {
            var path = _resolver.ResolveAssemblyToPath(assemblyName);
            return path is null ? null : LoadFromAssemblyPath(path);
        }

        protected override IntPtr LoadUnmanagedDll(string unmanagedDllName)
        {
            var path = _resolver.ResolveUnmanagedDllToPath(unmanagedDllName);
            return path is null ? IntPtr.Zero : LoadUnmanagedDllFromPath(path);
        }
    }

    private sealed record EngineHostProcess(
        Process Process,
        StringBuilder Stdout,
        StringBuilder Stderr)
    {
        public string StderrTail()
        {
            lock (Stderr)
            {
                var text = Stderr.ToString();
                return text.Length > 4000 ? text[^4000..] : text;
            }
        }
    }
}
