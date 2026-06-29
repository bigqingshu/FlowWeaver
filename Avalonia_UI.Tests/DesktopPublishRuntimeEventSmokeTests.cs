using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Sockets;
using System.Reflection;
using System.Runtime.Loader;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class DesktopPublishRuntimeEventSmokeTests
{
    [TestMethod]
    public async Task PublishedDesktopRuntimeEventClientReceivesEngineReady()
    {
        var repoRoot = FindRepoRoot();
        var pythonExe = RepoPythonExe(repoRoot);
        RunCommand(
            pythonExe,
            new[] { "tools\\create_portable_layout.py", "--no-desktop-build" },
            repoRoot);
        RunCommand(pythonExe, new[] { "tools\\publish_desktop.py" }, repoRoot);

        var portableRoot = Path.Combine(repoRoot, ".tmp", "FlowWeaverPortable");
        var engineHostDir = Path.Combine(portableRoot, "EngineHost");
        var desktopDir = Path.Combine(portableRoot, "Desktop");
        var publishedAssemblyPath = Path.Combine(desktopDir, "Avalonia_UI.dll");
        Assert.IsTrue(File.Exists(Path.Combine(desktopDir, "Avalonia_UI.exe")));
        Assert.IsTrue(File.Exists(publishedAssemblyPath));

        var port = FreePort();
        var process = StartPortableEngineHost(engineHostDir, port);
        try
        {
            var baseUrl = $"http://127.0.0.1:{port}";
            await WaitForPublishedHealthAsync(baseUrl, process);

            var token = File.ReadAllText(
                Path.Combine(
                    engineHostDir,
                    "runtime",
                    "config",
                    "local_api_token"))
                .Trim();
            Assert.IsFalse(string.IsNullOrWhiteSpace(token));

            var loadContext = new PublishedDesktopLoadContext(publishedAssemblyPath);
            try
            {
                var assembly = loadContext.LoadFromAssemblyPath(publishedAssemblyPath);
                var client = Activator.CreateInstance(
                    RequiredType(
                        assembly,
                        "Avalonia_UI.Api.EngineHostRuntimeEventStreamClient"))!;
                var settings = CreateConnectionSettings(assembly, baseUrl, token);

                object? stream = null;
                try
                {
                    stream = await ConnectPublishedRuntimeEventStreamAsync(
                        client,
                        settings);
                    var runtimeEvent = await ReadNextPublishedEventAsync(stream);

                    Assert.AreEqual(
                        "ENGINE_READY",
                        Property<string>(runtimeEvent, "EventType"));
                    Assert.IsNull(Property<string?>(runtimeEvent, "WorkflowRunId"));
                }
                finally
                {
                    if (stream is not null)
                    {
                        await DisposePublishedStreamAsync(stream);
                    }
                }
            }
            finally
            {
                loadContext.Unload();
            }
        }
        finally
        {
            StopProcess(process);
        }
    }

    private static object CreateConnectionSettings(
        Assembly assembly,
        string baseUrl,
        string token)
    {
        var settingsType = RequiredType(
            assembly,
            "Avalonia_UI.Models.EngineHostConnectionSettings");
        var settings = Activator.CreateInstance(settingsType)!;
        settingsType.GetProperty("BaseUrl")!.SetValue(settings, baseUrl);
        settingsType.GetProperty("Token")!.SetValue(settings, token);
        return settings;
    }

    private static async Task<object> ConnectPublishedRuntimeEventStreamAsync(
        object client,
        object settings)
    {
        var method = client.GetType()
            .GetMethods()
            .Single(item =>
                item.Name == "ConnectAsync"
                && item.GetParameters().Length == 2);
        using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        var task = (Task)method.Invoke(
            client,
            new object?[] { settings, cancellation.Token })!;
        await task.ConfigureAwait(false);
        return task.GetType().GetProperty("Result")!.GetValue(task)!;
    }

    private static async Task<object> ReadNextPublishedEventAsync(object stream)
    {
        var method = stream.GetType()
            .GetMethods()
            .Single(item =>
                item.Name == "ReadNextAsync"
                && item.GetParameters().Length == 1);
        using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        var task = (Task)method.Invoke(
            stream,
            new object?[] { cancellation.Token })!;
        await task.ConfigureAwait(false);
        var runtimeEvent = task.GetType().GetProperty("Result")!.GetValue(task);
        Assert.IsNotNull(runtimeEvent);
        return runtimeEvent!;
    }

    private static async Task DisposePublishedStreamAsync(object stream)
    {
        var method = stream.GetType().GetMethod("DisposeAsync")!;
        var result = method.Invoke(stream, Array.Empty<object>());
        switch (result)
        {
            case ValueTask valueTask:
                await valueTask.ConfigureAwait(false);
                break;
            case Task task:
                await task.ConfigureAwait(false);
                break;
            case null:
                break;
            default:
                Assert.Fail(
                    $"Unexpected DisposeAsync return type: {result.GetType().FullName}");
                break;
        }
    }

    private static async Task WaitForPublishedHealthAsync(
        string baseUrl,
        EngineHostProcess process)
    {
        using var httpClient = new HttpClient { Timeout = TimeSpan.FromSeconds(2) };
        var deadline = DateTimeOffset.UtcNow.AddSeconds(20);
        string? lastResponse = null;
        Exception? lastException = null;
        while (DateTimeOffset.UtcNow < deadline)
        {
            AssertProcessRunning(process);
            try
            {
                using var response = await httpClient.GetAsync(
                    $"{baseUrl}/api/v1/health");
                lastResponse = await response.Content.ReadAsStringAsync();
                if (response.IsSuccessStatusCode)
                {
                    return;
                }
            }
            catch (HttpRequestException ex)
            {
                lastException = ex;
            }
            catch (TaskCanceledException ex)
            {
                lastException = ex;
            }

            await Task.Delay(100);
        }

        Assert.Fail(
            "EngineHost health did not become ok. "
            + $"Last response: {lastResponse}. "
            + $"Last exception: {lastException?.Message}. "
            + $"stderr: {process.StderrTail()}");
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
