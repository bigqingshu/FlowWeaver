using System;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using Avalonia_UI.Services;
using Avalonia_UI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class RunOverviewViewModelTests
{
    private static readonly EngineHostConnectionSettings Settings = new()
    {
        Token = "secret",
    };

    [TestMethod]
    public async Task ContextDoesNotLoadUntilOverviewBecomesActive()
    {
        var service = new FakeRunReviewService
        {
            Handler = (runId, _) => Success(Review(runId)),
        };
        var viewModel = CreateViewModel(service);

        viewModel.SetContext(Settings, "run-1", actionsEnabled: true);

        Assert.AreEqual(0, service.Calls);
        Assert.IsNull(viewModel.Review);

        viewModel.SetActive(true);
        await viewModel.WaitForPendingLoadAsync();

        Assert.AreEqual(1, service.Calls);
        Assert.AreEqual("run-1", viewModel.RunIdText);
        Assert.AreEqual("Node runs: 1 | tables: 2 | readable: 1", viewModel.CountsText);
        Assert.AreEqual("runtime_sqlite: 2", viewModel.StorageKindsText);
    }

    [TestMethod]
    public async Task FastRunSwitchCancelsOldRequestAndIgnoresLateReview()
    {
        var firstResponse = new TaskCompletionSource<ApiResponseEnvelope<RunReviewDto>>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        var firstCancelled = false;
        var service = new FakeRunReviewService
        {
            Handler = (runId, cancellationToken) =>
            {
                if (runId == "run-1")
                {
                    cancellationToken.Register(() => firstCancelled = true);
                    return firstResponse.Task;
                }

                return Success(Review(runId));
            },
        };
        var viewModel = CreateViewModel(service);
        viewModel.SetActive(true);

        viewModel.SetContext(Settings, "run-1", actionsEnabled: true);
        var firstLoad = viewModel.WaitForPendingLoadAsync();
        viewModel.SetContext(Settings, "run-2", actionsEnabled: true);
        await viewModel.WaitForPendingLoadAsync();
        firstResponse.SetResult(ApiResponseEnvelope<RunReviewDto>.Success(Review("run-1")));
        await firstLoad;

        Assert.IsTrue(firstCancelled);
        Assert.AreEqual("run-2", viewModel.RunIdText);
        Assert.AreEqual("SUCCEEDED", viewModel.StatusText);
    }

    [TestMethod]
    public void ClearingSelectionClearsPreviousReviewImmediately()
    {
        var service = new FakeRunReviewService();
        var viewModel = CreateViewModel(service);
        viewModel.SetActive(true);

        viewModel.SetContext(Settings, null, actionsEnabled: true);

        Assert.IsNull(viewModel.Review);
        Assert.AreEqual("Select a run to view its review.", viewModel.Message);
        Assert.IsFalse(viewModel.RefreshCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task ApiFailureIsSeparateFromRunErrorJson()
    {
        var service = new FakeRunReviewService
        {
            Handler = (_, _) => Task.FromResult(
                ApiResponseEnvelope<RunReviewDto>.Failure("RUN_NOT_FOUND", "missing")),
        };
        var viewModel = CreateViewModel(service);
        viewModel.SetActive(true);

        viewModel.SetContext(Settings, "run-missing", actionsEnabled: true);
        await viewModel.WaitForPendingLoadAsync();

        Assert.AreEqual("RUN_NOT_FOUND: missing", viewModel.ErrorMessage);
        Assert.IsFalse(viewModel.HasRunError);
        Assert.IsNull(viewModel.Review);
    }

    private static RunOverviewViewModel CreateViewModel(FakeRunReviewService service)
    {
        return new RunOverviewViewModel(
            service,
            key => key switch
            {
                "common.on" => "On",
                "common.off" => "Off",
                "runs.overview.select_run" => "Select a run to view its review.",
                "runs.overview.activate" => "Open the overview tab to load the run review.",
                "runs.overview.ready" => "Run review is ready to load.",
                "runs.overview.loading" => "Loading run review...",
                "runs.overview.loaded" => "Run review loaded.",
                "runs.overview.load_failed" => "Run review load failed.",
                "runs.overview.counts_format" => "Node runs: {0} | tables: {1} | readable: {2}",
                "runs.overview.preview_format" => "Paged rows: {0} | embedded rows: {1} | readable IDs: {2}",
                _ => key,
            });
    }

    private static RunReviewDto Review(string workflowRunId)
    {
        return new RunReviewDto
        {
            Run = new WorkflowRunDto
            {
                WorkflowRunId = workflowRunId,
                WorkflowId = "wf-1",
                WorkflowVersion = 2,
                Status = "SUCCEEDED",
                RunMode = "full",
                TriggerSource = "background_manual",
            },
            NodeRuns =
            [
                new NodeRunDto
                {
                    NodeRunId = "node-run-1",
                    WorkflowRunId = workflowRunId,
                    NodeInstanceId = "source",
                    NodeType = "SourceNode",
                    Status = "SUCCEEDED",
                },
            ],
            TableRefSummary = new RunReviewTableRefSummaryDto
            {
                Total = 2,
                Readable = 1,
                ByStorageKind = new() { ["runtime_sqlite"] = 2 },
                ByLifecycleStatus = new() { ["ACTIVE"] = 1, ["RELEASED"] = 1 },
            },
            DataPreview = new RunReviewDataPreviewDto
            {
                UsesPagedRows = true,
                ReadableTableRefIds = ["table-1"],
            },
        };
    }

    private static Task<ApiResponseEnvelope<RunReviewDto>> Success(RunReviewDto review)
    {
        return Task.FromResult(ApiResponseEnvelope<RunReviewDto>.Success(review));
    }

    private sealed class FakeRunReviewService : IRunReviewService
    {
        public Func<string, CancellationToken, Task<ApiResponseEnvelope<RunReviewDto>>> Handler
            { get; set; } = (runId, _) => Success(Review(runId));

        public int Calls { get; private set; }

        public Task<ApiResponseEnvelope<RunReviewDto>> GetAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            Calls++;
            return Handler(workflowRunId, cancellationToken);
        }
    }
}
