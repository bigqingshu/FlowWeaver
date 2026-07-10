using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using Avalonia_UI.Services;
using Avalonia_UI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class RunLoopMonitorViewModelTests
{
    [TestMethod]
    public async Task SelectionLoadsLoopsThenIterationsThenDetails()
    {
        var loopService = new FakeLoopRunQueryService
        {
            LoopsHandler = (_, _, _, _) => Success([Loop("loop-run-1", "run-1")]),
            IterationsHandler = (_, _, _, _, _) =>
                Success([Iteration("iteration-1", "loop-run-1")]),
            NodesHandler = (_, _, _, _) => Success([IterationNode("iteration-1")]),
            TablesHandler = (_, _, _, _, _) => Success([IterationTable("iteration-1")]),
        };
        var directoryService = new FakeRunTableDirectoryService();
        var viewModel = CreateViewModel(loopService, directoryService);

        await viewModel.SelectRunAsync(Settings, "run-1");

        Assert.HasCount(1, viewModel.Loops);
        Assert.AreEqual(0, loopService.IterationCalls);
        Assert.AreEqual(0, loopService.NodeCalls);
        Assert.AreEqual(0, loopService.TableCalls);

        viewModel.SelectedLoop = viewModel.Loops[0];
        await viewModel.WaitForPendingLoadAsync();

        Assert.HasCount(1, viewModel.Iterations);
        Assert.AreEqual(1, loopService.IterationCalls);
        Assert.AreEqual(0, loopService.NodeCalls);

        viewModel.SelectedIteration = viewModel.Iterations[0];
        await viewModel.WaitForPendingLoadAsync();

        Assert.HasCount(1, viewModel.IterationNodes);
        Assert.HasCount(1, viewModel.IterationTableRefs);
        Assert.AreEqual(1, loopService.NodeCalls);
        Assert.AreEqual(1, loopService.TableCalls);
    }

    [TestMethod]
    public async Task FastRunSwitchCancelsOldRequestAndIgnoresLateResponse()
    {
        var firstResponse = new TaskCompletionSource<
            ApiResponseEnvelope<List<LoopRunDto>>>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        var firstRequestCancelled = false;
        var loopService = new FakeLoopRunQueryService
        {
            LoopsHandler = (runId, _, _, cancellationToken) =>
            {
                if (runId == "run-1")
                {
                    cancellationToken.Register(() => firstRequestCancelled = true);
                    return firstResponse.Task;
                }

                return Success([Loop("loop-run-2", "run-2")]);
            },
        };
        var viewModel = CreateViewModel(
            loopService,
            new FakeRunTableDirectoryService());

        var firstLoad = viewModel.SelectRunAsync(Settings, "run-1");
        await viewModel.SelectRunAsync(Settings, "run-2");
        firstResponse.SetResult(
            ApiResponseEnvelope<List<LoopRunDto>>.Success(
                new List<LoopRunDto> { Loop("loop-run-1", "run-1") }));
        await firstLoad;

        Assert.IsTrue(firstRequestCancelled);
        Assert.HasCount(1, viewModel.Loops);
        Assert.AreEqual("loop-run-2", viewModel.Loops[0].LoopRunId);
    }

    [TestMethod]
    public async Task EmptyRunIsNormalStateAndPaginationDoesNotDuplicateItems()
    {
        var calls = 0;
        var firstPage = Enumerable.Range(0, 50)
            .Select(index => Loop($"loop-{index}", "run-1"))
            .ToList();
        var loopService = new FakeLoopRunQueryService
        {
            LoopsHandler = (_, offset, _, _) =>
            {
                calls++;
                return offset == 0
                    ? Success(firstPage)
                    : Success([firstPage[49], Loop("loop-50", "run-1")]);
            },
        };
        var viewModel = CreateViewModel(
            loopService,
            new FakeRunTableDirectoryService());

        await viewModel.SelectRunAsync(Settings, "run-1");
        await viewModel.LoadMoreLoopsCommand.ExecuteAsync(null);

        Assert.AreEqual(2, calls);
        Assert.HasCount(51, viewModel.Loops);
        Assert.AreEqual(1, viewModel.Loops.Count(loop => loop.LoopRunId == "loop-49"));
        Assert.IsNull(viewModel.ErrorMessage);

        loopService.LoopsHandler = (_, _, _, _) => Success<LoopRunDto>([]);
        await viewModel.SelectRunAsync(Settings, "run-empty");
        Assert.IsEmpty(viewModel.Loops);
        Assert.AreEqual("runs.loop_monitor.empty", viewModel.Message);
        Assert.IsNull(viewModel.ErrorMessage);
    }

    [TestMethod]
    public async Task RunMetadataCacheReusesPagedNodeAndTableMetadata()
    {
        var directoryService = new FakeRunTableDirectoryService();
        var loopService = new FakeLoopRunQueryService();
        var cache = new RunMetadataCache(directoryService, loopService);

        await cache.GetNodeRunsAsync(Settings, "run-1", limit: 25);
        await cache.GetNodeRunsAsync(Settings, "run-1", limit: 25);
        await cache.GetTableRefsAsync(Settings, "run-1", limit: 25);
        await cache.GetTableRefsAsync(Settings, "run-1", limit: 25);

        Assert.AreEqual(1, directoryService.NodeCalls);
        Assert.AreEqual(1, directoryService.TableCalls);
    }

    [TestMethod]
    public async Task SwitchingRunCancelsQueuedRefreshForPreviousRun()
    {
        var refreshGate = new TaskCompletionSource(
            TaskCreationOptions.RunContinuationsAsynchronously);
        var loopService = new FakeLoopRunQueryService
        {
            LoopsHandler = (runId, _, _, _) => Success(
                [Loop($"loop-{runId}", runId)]),
        };
        var viewModel = new RunLoopMonitorViewModel(
            loopService,
            new RunMetadataCache(
                new FakeRunTableDirectoryService(),
                loopService),
            key => key,
            _ => refreshGate.Task);
        await viewModel.SelectRunAsync(Settings, "run-1");
        viewModel.QueueRefresh(Settings, "run-1");

        await viewModel.SelectRunAsync(Settings, "run-2");
        refreshGate.SetResult();
        await viewModel.WaitForPendingRefreshAsync();

        Assert.HasCount(1, viewModel.Loops);
        Assert.AreEqual("loop-run-2", viewModel.Loops[0].LoopRunId);
    }

    private static readonly EngineHostConnectionSettings Settings = new()
    {
        Token = "secret",
    };

    private static RunLoopMonitorViewModel CreateViewModel(
        FakeLoopRunQueryService loopService,
        FakeRunTableDirectoryService directoryService)
    {
        return new RunLoopMonitorViewModel(
            loopService,
            new RunMetadataCache(directoryService, loopService),
            key => key,
            _ => Task.CompletedTask);
    }

    private static LoopRunDto Loop(string loopRunId, string workflowRunId)
    {
        return new LoopRunDto
        {
            LoopRunId = loopRunId,
            WorkflowRunId = workflowRunId,
            LoopId = loopRunId,
            StartNodeInstanceId = "start",
            JudgeNodeInstanceId = "judge",
            Status = "RUNNING",
            CurrentIteration = 1,
            MaxIterations = 3,
        };
    }

    private static LoopIterationRunDto Iteration(string iterationId, string loopRunId)
    {
        return new LoopIterationRunDto
        {
            LoopIterationId = iterationId,
            LoopRunId = loopRunId,
            IterationIndex = 0,
            Status = "RUNNING",
        };
    }

    private static LoopIterationNodeRunDto IterationNode(string iterationId)
    {
        return new LoopIterationNodeRunDto
        {
            LoopIterationId = iterationId,
            NodeRunId = "node-run-1",
            NodeInstanceId = "body",
            Role = "BODY",
            NodeType = "FilterRowsNode",
            Status = "RUNNING",
            Attempt = 1,
        };
    }

    private static LoopIterationTableRefDto IterationTable(string iterationId)
    {
        return new LoopIterationTableRefDto
        {
            LoopIterationId = iterationId,
            TableRefId = "table-1",
            Role = "OUTPUT",
            LogicalTableId = "orders",
            SourceNodeInstanceId = "body",
            OutputSlot = "result",
        };
    }

    private static Task<ApiResponseEnvelope<List<T>>> Success<T>(IEnumerable<T> values)
    {
        return Task.FromResult(
            ApiResponseEnvelope<List<T>>.Success(values.ToList()));
    }

    private sealed class FakeLoopRunQueryService : ILoopRunQueryService
    {
        public Func<string, int, int, CancellationToken, Task<ApiResponseEnvelope<List<LoopRunDto>>>>
            LoopsHandler { get; set; } = (_, _, _, _) => Success<LoopRunDto>([]);

        public Func<string, string, int, int, CancellationToken, Task<ApiResponseEnvelope<List<LoopIterationRunDto>>>>
            IterationsHandler { get; set; } = (_, _, _, _, _) => Success<LoopIterationRunDto>([]);

        public Func<string, string, string, CancellationToken, Task<ApiResponseEnvelope<List<LoopIterationNodeRunDto>>>>
            NodesHandler { get; set; } = (_, _, _, _) => Success<LoopIterationNodeRunDto>([]);

        public Func<string, string, string, string?, CancellationToken, Task<ApiResponseEnvelope<List<LoopIterationTableRefDto>>>>
            TablesHandler { get; set; } = (_, _, _, _, _) => Success<LoopIterationTableRefDto>([]);

        public int IterationCalls { get; private set; }

        public int NodeCalls { get; private set; }

        public int TableCalls { get; private set; }

        public Task<ApiResponseEnvelope<List<LoopRunDto>>> ListLoopsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            int offset = 0,
            int limit = 50,
            IReadOnlyCollection<string>? statuses = null,
            CancellationToken cancellationToken = default)
        {
            return LoopsHandler(workflowRunId, offset, limit, cancellationToken);
        }

        public Task<ApiResponseEnvelope<List<LoopIterationRunDto>>> ListIterationsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            string loopRunId,
            int offset = 0,
            int limit = 50,
            IReadOnlyCollection<string>? statuses = null,
            CancellationToken cancellationToken = default)
        {
            IterationCalls++;
            return IterationsHandler(
                workflowRunId,
                loopRunId,
                offset,
                limit,
                cancellationToken);
        }

        public Task<ApiResponseEnvelope<List<LoopIterationNodeRunDto>>> ListIterationNodesAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            string loopRunId,
            string loopIterationId,
            CancellationToken cancellationToken = default)
        {
            NodeCalls++;
            return NodesHandler(
                workflowRunId,
                loopRunId,
                loopIterationId,
                cancellationToken);
        }

        public Task<ApiResponseEnvelope<List<LoopIterationTableRefDto>>> ListIterationTableRefsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            string loopRunId,
            string loopIterationId,
            string? role = null,
            CancellationToken cancellationToken = default)
        {
            TableCalls++;
            return TablesHandler(
                workflowRunId,
                loopRunId,
                loopIterationId,
                role,
                cancellationToken);
        }
    }

    private sealed class FakeRunTableDirectoryService : IRunTableDirectoryService
    {
        public int NodeCalls { get; private set; }

        public int TableCalls { get; private set; }

        public Task<ApiResponseEnvelope<NodeRunPageDto>> ListNodeRunsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            int offset = 0,
            int limit = 100,
            IReadOnlyCollection<string>? statuses = null,
            CancellationToken cancellationToken = default)
        {
            NodeCalls++;
            return Task.FromResult(
                ApiResponseEnvelope<NodeRunPageDto>.Success(new NodeRunPageDto()));
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
            TableCalls++;
            return Task.FromResult(
                ApiResponseEnvelope<RunTableDirectoryPageDto>.Success(
                    new RunTableDirectoryPageDto()));
        }
    }
}
