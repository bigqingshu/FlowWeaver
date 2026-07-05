using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class EngineHostFormalSmokeTests
{
    private const string InitialDefinitionJson =
        """
        {"schema_version":"1.0","nodes":[],"connections":[]}
        """;

    private const string RunnableDefinitionJson =
        """
        {
          "schema_version": "1.0",
          "nodes": [
            {
              "node_instance_id": "generate",
              "node_type": "GenerateTestTableNode",
              "node_version": "1.0",
              "config": {
                "rows": 3,
                "columns": ["row_id", "amount"]
              }
            },
            {
              "node_instance_id": "filter",
              "node_type": "FilterRowsNode",
              "node_version": "1.0",
              "config": {
                "field": "row_id",
                "operator": "GE",
                "value": 2
              }
            },
            {
              "node_instance_id": "publish",
              "node_type": "PublishSharedTablesNode",
              "node_version": "1.0",
              "config": {
                "share_name": "n0.orders",
                "export_names": ["orders"]
              }
            }
          ],
          "connections": [
            {
              "connection_id": "generate-filter",
              "source_node_id": "generate",
              "source_port": "out",
              "target_node_id": "filter",
              "target_port": "in"
            },
            {
              "connection_id": "filter-publish",
              "source_node_id": "filter",
              "source_port": "out",
              "target_node_id": "publish",
              "target_port": "in"
            }
          ]
        }
        """;

    [TestMethod]
    public async Task AvaloniaApiClientRunsFormalDefinitionEditAndRunLoop()
    {
        var repoRoot = FindRepoRoot();
        var runRoot = Path.Combine(
            Path.GetTempPath(),
            $"flowweaver-n0-{Guid.NewGuid():N}");
        Directory.CreateDirectory(runRoot);
        PrepareEngineHostRunRoot(repoRoot, runRoot);

        var port = FreePort();
        var process = StartEngineHost(repoRoot, runRoot, port);
        try
        {
            var client = new EngineHostApiClient();
            var settings = new EngineHostConnectionSettings
            {
                BaseUrl = $"http://127.0.0.1:{port}",
            };

            var health = await WaitForHealthAsync(client, settings, process);
            Assert.AreEqual("ok", health.Status);

            var token = await File.ReadAllTextAsync(
                Path.Combine(runRoot, "runtime", "config", "local_api_token"));
            settings = new EngineHostConnectionSettings
            {
                BaseUrl = settings.BaseUrl,
                Token = token.Trim(),
            };
            Assert.IsFalse(string.IsNullOrWhiteSpace(settings.Token));

            var nodeDefinitions = AssertOk(
                await client.ListNodeDefinitionsAsync(settings));
            CollectionAssert.IsSubsetOf(
                new[] { "GenerateTestTableNode", "FilterRowsNode", "PublishSharedTablesNode" },
                nodeDefinitions.Select(item => item.NodeType).ToList());

            using var initialDefinition = JsonDocument.Parse(InitialDefinitionJson);
            var created = AssertOk(
                await client.CreateWorkflowAsync(
                    settings,
                    "N0 formal loop",
                    initialDefinition.RootElement));
            Assert.AreEqual(1, created.Version);

            var detailBeforeSave = AssertOk(
                await client.GetWorkflowAsync(settings, created.WorkflowId));
            Assert.AreEqual(created.RevisionId, detailBeforeSave.RevisionId);

            using var runnableDefinition = JsonDocument.Parse(RunnableDefinitionJson);
            var validation = AssertOk(
                await client.ValidateWorkflowDraftAsync(
                    settings,
                    runnableDefinition.RootElement));
            Assert.IsTrue(validation.Valid);

            var saved = AssertOk(
                await client.UpdateWorkflowAsync(
                    settings,
                    created.WorkflowId,
                    "N0 formal loop",
                    runnableDefinition.RootElement,
                    detailBeforeSave.RevisionId));
            Assert.AreEqual(2, saved.Version);
            Assert.AreNotEqual(detailBeforeSave.RevisionId, saved.RevisionId);

            var revisions = AssertOk(
                await client.ListWorkflowRevisionsAsync(settings, created.WorkflowId));
            CollectionAssert.AreEqual(
                new[] { 1, 2 },
                revisions.Select(item => item.Version).OrderBy(item => item).ToArray());

            var streamClient = new EngineHostRuntimeEventStreamClient();
            await using var stream = await streamClient.ConnectAsync(settings);
            var ready = await ReadNextEventAsync(stream, "ENGINE_READY");
            Assert.IsNull(ready.WorkflowRunId);

            var started = AssertOk(
                await client.StartWorkflowRunAsync(settings, created.WorkflowId));
            Assert.AreEqual(saved.RevisionId, started.RevisionId);

            var terminal = await WaitForTerminalRunAsync(
                client,
                settings,
                created.WorkflowId,
                started.WorkflowRunId,
                process);
            Assert.AreEqual("SUCCEEDED", terminal.Status);

            var websocketEvents = await CollectWorkflowEventsAsync(
                stream,
                started.WorkflowRunId,
                new HashSet<string> { "WORKFLOW_STARTED", "WORKFLOW_FINISHED" });
            CollectionAssert.IsSubsetOf(
                new[] { "WORKFLOW_STARTED", "WORKFLOW_FINISHED" },
                websocketEvents.Select(item => item.EventType).ToList());

            var nodeRuns = AssertOk(
                await client.ListNodeRunsAsync(settings, started.WorkflowRunId));
            CollectionAssert.AreEquivalent(
                new[] { "generate", "filter", "publish" },
                nodeRuns.Select(item => item.NodeInstanceId).ToArray());
            Assert.IsTrue(nodeRuns.All(item => item.Status == "SUCCEEDED"));

            var tableRefs = AssertOk(
                await client.ListTableRefsAsync(settings, started.WorkflowRunId));
            Assert.AreEqual(
                2,
                tableRefs.Count(item => item.LifecycleStatus == "PUBLISHED"));

            var publications = AssertOk(
                await client.ListSharedPublicationsAsync(
                    settings,
                    shareName: "n0.orders"));
            Assert.HasCount(1, publications);
            Assert.AreEqual(1, publications[0].PublicationVersion);
            CollectionAssert.AreEqual(
                new[] { "orders" },
                publications[0].Members.Select(item => item.ExportName).ToArray());

            var runtimeEvents = AssertOk(
                await client.ListEventsAsync(
                    settings,
                    workflowRunId: started.WorkflowRunId,
                    limit: 100));
            CollectionAssert.IsSubsetOf(
                new[] { "WORKFLOW_STARTED", "WORKFLOW_FINISHED" },
                runtimeEvents.Select(item => item.EventType).ToList());
        }
        finally
        {
            StopProcess(process);
            TryDeleteDirectory(runRoot);
        }
    }

    private static async Task<HealthStatusDto> WaitForHealthAsync(
        EngineHostApiClient client,
        EngineHostConnectionSettings settings,
        EngineHostProcess process)
    {
        var deadline = DateTimeOffset.UtcNow.AddSeconds(20);
        ApiResponseEnvelope<HealthStatusDto>? lastResponse = null;
        while (DateTimeOffset.UtcNow < deadline)
        {
            AssertProcessRunning(process);
            lastResponse = await client.GetHealthAsync(settings);
            if (lastResponse.Ok && lastResponse.Data is not null)
            {
                return lastResponse.Data;
            }

            await Task.Delay(100);
        }

        Assert.Fail(
            "EngineHost health did not become ok. "
            + $"Last response: {lastResponse?.Error?.ErrorCode} "
            + $"{lastResponse?.Error?.Message}. "
            + $"stderr: {process.StderrTail()}");
        throw new UnreachableException();
    }

    private static async Task<WorkflowRunDto> WaitForTerminalRunAsync(
        EngineHostApiClient client,
        EngineHostConnectionSettings settings,
        string workflowId,
        string workflowRunId,
        EngineHostProcess process)
    {
        var terminalStatuses = new HashSet<string>
        {
            "SUCCEEDED",
            "FAILED",
            "CANCELLED",
            "ABORTED",
        };
        var deadline = DateTimeOffset.UtcNow.AddSeconds(30);
        WorkflowRunDto? lastRun = null;
        while (DateTimeOffset.UtcNow < deadline)
        {
            AssertProcessRunning(process);
            var runs = AssertOk(await client.ListRunsAsync(settings, workflowId));
            lastRun = runs.SingleOrDefault(item => item.WorkflowRunId == workflowRunId);
            if (lastRun is not null && terminalStatuses.Contains(lastRun.Status))
            {
                return lastRun;
            }

            await Task.Delay(250);
        }

        Assert.Fail(
            "Workflow run did not finish. "
            + $"Last status: {lastRun?.Status ?? "<missing>"}. "
            + $"stderr: {process.StderrTail()}");
        throw new UnreachableException();
    }

    private static async Task<RuntimeEventDto> ReadNextEventAsync(
        IEngineHostRuntimeEventStream stream,
        string expectedEventType)
    {
        using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        var runtimeEvent = await stream.ReadNextAsync(cancellation.Token);
        Assert.IsNotNull(runtimeEvent);
        Assert.AreEqual(expectedEventType, runtimeEvent!.EventType);
        return runtimeEvent;
    }

    private static async Task<List<RuntimeEventDto>> CollectWorkflowEventsAsync(
        IEngineHostRuntimeEventStream stream,
        string workflowRunId,
        HashSet<string> requiredEventTypes)
    {
        var events = new List<RuntimeEventDto>();
        var deadline = DateTimeOffset.UtcNow.AddSeconds(10);
        while (DateTimeOffset.UtcNow < deadline)
        {
            using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(1));
            try
            {
                var runtimeEvent = await stream.ReadNextAsync(cancellation.Token);
                if (runtimeEvent?.WorkflowRunId == workflowRunId)
                {
                    events.Add(runtimeEvent);
                    if (requiredEventTypes.IsSubsetOf(
                        events.Select(item => item.EventType).ToHashSet()))
                    {
                        return events;
                    }
                }
            }
            catch (OperationCanceledException)
            {
            }
        }

        Assert.Fail(
            "Required WebSocket runtime events were not observed. "
            + $"Observed: {string.Join(", ", events.Select(item => item.EventType))}");
        throw new UnreachableException();
    }

    private static TData AssertOk<TData>(ApiResponseEnvelope<TData> response)
        where TData : class
    {
        Assert.IsTrue(
            response.Ok,
            response.Error is null
                ? "Expected API response to be ok."
                : $"{response.Error.ErrorCode}: {response.Error.Message}");
        Assert.IsNotNull(response.Data);
        return response.Data!;
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

    private static EngineHostProcess StartEngineHost(
        string repoRoot,
        string runRoot,
        int port)
    {
        var pythonExe = Path.Combine(repoRoot, "python312", "python.exe");
        if (!File.Exists(pythonExe))
        {
            pythonExe = "python";
        }

        var startInfo = new ProcessStartInfo
        {
            FileName = pythonExe,
            WorkingDirectory = runRoot,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
        startInfo.ArgumentList.Add("-m");
        startInfo.ArgumentList.Add("uvicorn");
        startInfo.ArgumentList.Add("--app-dir");
        startInfo.ArgumentList.Add(Path.Combine(repoRoot, "src"));
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

    private static void PrepareEngineHostRunRoot(string repoRoot, string runRoot)
    {
        File.Copy(
            Path.Combine(repoRoot, "alembic.ini"),
            Path.Combine(runRoot, "alembic.ini"));
        CopyDirectory(
            Path.Combine(repoRoot, "migrations"),
            Path.Combine(runRoot, "migrations"));
    }

    private static string FindRepoRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            if (File.Exists(Path.Combine(directory.FullName, "pyproject.toml"))
                && Directory.Exists(Path.Combine(directory.FullName, "src", "flowweaver")))
            {
                return directory.FullName;
            }

            directory = directory.Parent;
        }

        throw new DirectoryNotFoundException("FlowWeaver repository root was not found.");
    }

    private static int FreePort()
    {
        using var listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        return ((IPEndPoint)listener.LocalEndpoint).Port;
    }

    private static void CopyDirectory(string sourceDirectory, string targetDirectory)
    {
        Directory.CreateDirectory(targetDirectory);
        foreach (var sourceFile in Directory.EnumerateFiles(sourceDirectory))
        {
            File.Copy(
                sourceFile,
                Path.Combine(targetDirectory, Path.GetFileName(sourceFile)));
        }

        foreach (var childSourceDirectory in Directory.EnumerateDirectories(sourceDirectory))
        {
            CopyDirectory(
                childSourceDirectory,
                Path.Combine(targetDirectory, Path.GetFileName(childSourceDirectory)));
        }
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
