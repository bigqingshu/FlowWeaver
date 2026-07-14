using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using Avalonia_UI.Services;
using Avalonia_UI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeRunMonitorViewModelTests
{
    private static readonly EngineHostConnectionSettings Settings = new()
    {
        Token = "secret",
    };

    [TestMethod]
    public async Task MoreThanOneHundredNodesUsesBackendPagination()
    {
        var service = new FakeRunTableDirectoryService
        {
            Handler = (runId, offset, limit, _, _) => Task.FromResult(
                ApiResponseEnvelope<NodeRunPageDto>.Success(
                    offset == 0
                        ? Page(runId, offset, limit, 101, true, 100)
                        : Page(runId, offset, limit, 101, false, 1))),
        };
        var viewModel = CreateViewModel(service);

        await viewModel.SelectRunAsync(Settings, "run-1", actionsEnabled: true);

        Assert.HasCount(100, viewModel.Nodes);
        Assert.IsTrue(viewModel.HasNextPage);
        Assert.AreEqual(0, viewModel.Offset);

        await viewModel.NextPageCommand.ExecuteAsync(null);

        Assert.HasCount(1, viewModel.Nodes);
        Assert.AreEqual(100, viewModel.Offset);
        Assert.AreEqual(101, viewModel.Total);
        Assert.AreEqual(100, service.Requests[1].Offset);
        Assert.AreEqual(NodeRunMonitorViewModel.PageSize, service.Requests[1].Limit);
    }

    [TestMethod]
    public async Task StatusFilterSendsRawProtocolValueAndResetsOffset()
    {
        var service = new FakeRunTableDirectoryService();
        var viewModel = CreateViewModel(service);
        await viewModel.SelectRunAsync(Settings, "run-1", actionsEnabled: true);
        viewModel.Offset = 100;

        viewModel.SelectedStatus = viewModel.StatusOptions.Single(
            option => option.Value == "RUNNING");
        await viewModel.WaitForPendingLoadAsync();

        Assert.AreEqual(0, viewModel.Offset);
        CollectionAssert.AreEqual(
            new[] { "RUNNING" },
            service.Requests[^1].Statuses?.ToArray());
    }

    [TestMethod]
    public async Task FastRunSwitchCancelsOldRequestAndIgnoresLatePage()
    {
        var firstResponse = new TaskCompletionSource<ApiResponseEnvelope<NodeRunPageDto>>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        var firstCancelled = false;
        var service = new FakeRunTableDirectoryService
        {
            Handler = (runId, offset, limit, _, cancellationToken) =>
            {
                if (runId == "run-1")
                {
                    cancellationToken.Register(() => firstCancelled = true);
                    return firstResponse.Task;
                }

                return Task.FromResult(ApiResponseEnvelope<NodeRunPageDto>.Success(
                    Page(runId, offset, limit, 1, false, 1)));
            },
        };
        var viewModel = CreateViewModel(service);

        var firstLoad = viewModel.SelectRunAsync(Settings, "run-1", actionsEnabled: true);
        await viewModel.SelectRunAsync(Settings, "run-2", actionsEnabled: true);
        firstResponse.SetResult(ApiResponseEnvelope<NodeRunPageDto>.Success(
            Page("run-1", 0, 100, 1, false, 1)));
        await firstLoad;

        Assert.IsTrue(firstCancelled);
        Assert.HasCount(1, viewModel.Nodes);
        Assert.AreEqual("run-2", viewModel.Nodes[0].WorkflowRunId);
    }

    [TestMethod]
    public async Task RefreshPreservesSelectionByNodeRunIdAndExposesDiagnostics()
    {
        var service = new FakeRunTableDirectoryService
        {
            Handler = (runId, offset, limit, _, _) => Task.FromResult(
                ApiResponseEnvelope<NodeRunPageDto>.Success(
                    new NodeRunPageDto
                    {
                        Items = [Node(runId, "node-run-1")],
                        Offset = offset,
                        Limit = limit,
                        Total = 1,
                    })),
        };
        var viewModel = CreateViewModel(service);
        await viewModel.SelectRunAsync(Settings, "run-1", actionsEnabled: true);
        viewModel.SelectedNodeRun = viewModel.Nodes[0];

        await viewModel.RefreshCommand.ExecuteAsync(null);

        Assert.AreEqual("node-run-1", viewModel.SelectedNodeRun?.NodeRunId);
        Assert.AreEqual("executor-1", viewModel.SelectedNodeRun?.ExecutorIdText);
        Assert.AreEqual(7, viewModel.SelectedNodeRun?.StateVersion);
        Assert.IsNotNull(viewModel.SelectedNodeRun);
        Assert.IsTrue(viewModel.SelectedNodeRun.HasError);
        StringAssert.Contains(viewModel.SelectedNodeRun?.ErrorJson ?? string.Empty, "NODE_FAILED");
    }

    private static NodeRunMonitorViewModel CreateViewModel(
        FakeRunTableDirectoryService service)
    {
        return new NodeRunMonitorViewModel(
            service,
            key => key switch
            {
                "runs.background.filter_all" => "All",
                "node_runs.select_run" => "Select a run to load node runs.",
                "node_runs.ready" => "Node runs are ready to load.",
                "node_runs.loading" => "Loading node runs...",
                "node_runs.loaded" => "Node run page loaded.",
                "node_runs.empty" => "No node runs match the current filter.",
                "node_runs.select_node" => "Select a node run to view details.",
                "node_runs.refresh_failed" => "Node status refresh failed.",
                "node_runs.page_format" => "Page {0} | total {1} | offset {2} | limit {3}",
                _ => key,
            });
    }

    private static NodeRunPageDto Page(
        string workflowRunId,
        int offset,
        int limit,
        int total,
        bool hasMore,
        int itemCount)
    {
        return new NodeRunPageDto
        {
            Items = Enumerable.Range(offset, itemCount)
                .Select(index => Node(workflowRunId, $"node-run-{index}"))
                .ToArray(),
            Offset = offset,
            Limit = limit,
            Total = total,
            HasMore = hasMore,
        };
    }

    private static NodeRunDto Node(string workflowRunId, string nodeRunId)
    {
        return new NodeRunDto
        {
            NodeRunId = nodeRunId,
            WorkflowRunId = workflowRunId,
            NodeInstanceId = $"node-{nodeRunId}",
            NodeType = "FilterRowsNode",
            Status = "FAILED",
            StateVersion = 7,
            ExecutorId = "executor-1",
            Progress = 0.5,
            CurrentStage = "filter",
            Attempt = 2,
            StartedAt = DateTimeOffset.Parse("2026-07-14T01:00:00Z"),
            FinishedAt = DateTimeOffset.Parse("2026-07-14T01:00:02Z"),
            LastHeartbeat = DateTimeOffset.Parse("2026-07-14T01:00:01Z"),
            Error = JsonSerializer.SerializeToElement(new { code = "NODE_FAILED" }),
        };
    }

    private sealed class FakeRunTableDirectoryService : IRunTableDirectoryService
    {
        public Func<string, int, int, IReadOnlyCollection<string>?, CancellationToken,
            Task<ApiResponseEnvelope<NodeRunPageDto>>> Handler { get; set; }
            = (runId, offset, limit, _, _) => Task.FromResult(
                ApiResponseEnvelope<NodeRunPageDto>.Success(
                    Page(runId, offset, limit, 0, false, 0)));

        public List<Request> Requests { get; } = new();

        public Task<ApiResponseEnvelope<NodeRunPageDto>> ListNodeRunsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            int offset = 0,
            int limit = 100,
            IReadOnlyCollection<string>? statuses = null,
            CancellationToken cancellationToken = default)
        {
            Requests.Add(new Request(workflowRunId, offset, limit, statuses));
            return Handler(workflowRunId, offset, limit, statuses, cancellationToken);
        }

        public Task<ApiResponseEnvelope<RunTableDirectoryPageDto>> ListTableRefsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            int offset = 0,
            int limit = 100,
            string? nodeRunId = null,
            string? tableType = null,
            IReadOnlyCollection<string>? lifecycleStatuses = null,
            string? logicalTableId = null,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
        }
    }

    private sealed record Request(
        string WorkflowRunId,
        int Offset,
        int Limit,
        IReadOnlyCollection<string>? Statuses);
}
