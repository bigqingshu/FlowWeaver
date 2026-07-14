using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;
using Avalonia_UI.Models;
using Avalonia_UI.Services;
using Avalonia_UI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class BackgroundRunManagementViewModelTests
{
    [TestMethod]
    public async Task StartUsesBackgroundServiceAndSelectsStartedRun()
    {
        var startedRun = Run(
            "run-background",
            "PENDING",
            triggerSource: "background_manual");
        var service = new FakeBackgroundRunService
        {
            StartResponse = ApiResponseEnvelope<WorkflowRunDto>.Success(startedRun),
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success([startedRun]),
        };
        var viewModel = CreateViewModel(service);

        await viewModel.StartCommand.ExecuteAsync(null);

        Assert.AreEqual("wf-1", service.LastStartedWorkflowId);
        Assert.AreEqual("full", service.LastStartedRunMode);
        Assert.AreEqual("run-background", viewModel.SelectedRun?.WorkflowRunId);
        Assert.AreEqual("background_manual", viewModel.SelectedRun?.TriggerSource);
    }

    [TestMethod]
    public async Task LoadPagePassesFiltersAndPagination()
    {
        var service = new FakeBackgroundRunService();
        var viewModel = new BackgroundRunManagementViewModel(service, key => key)
        {
            SelectedTriggerSource = null,
            SelectedRunMode = null,
            SelectedStatus = null,
        };
        viewModel.SelectedTriggerSource = viewModel.TriggerSourceOptions.Single(
            option => option.Value == "background_manual");
        viewModel.SelectedRunMode = viewModel.RunModeOptions.Single(
            option => option.Value == "preview_to_node");
        viewModel.SelectedStatus = viewModel.StatusOptions.Single(
            option => option.Value == "RUNNING");
        viewModel.SetContext(Settings(), "wf-1", canUseActions: true);
        viewModel.Offset = BackgroundRunManagementViewModel.PageSize;

        await viewModel.LoadPageAsync();

        Assert.AreEqual("wf-1", service.LastListRequest?.WorkflowId);
        CollectionAssert.AreEqual(
            new[] { "RUNNING" },
            service.LastListRequest?.Statuses?.ToArray());
        Assert.AreEqual("preview_to_node", service.LastListRequest?.RunMode);
        Assert.AreEqual("background_manual", service.LastListRequest?.TriggerSource);
        Assert.AreEqual(50, service.LastListRequest?.Offset);
        Assert.AreEqual(50, service.LastListRequest?.Limit);
    }

    [TestMethod]
    public async Task StatusFilterLocalizesDisplayTextAndPreservesRawValue()
    {
        var service = new FakeBackgroundRunService();
        var localizationService = new JsonLocalizationService();
        await localizationService.SetLanguageAsync("zh-Hans");
        var viewModel = new BackgroundRunManagementViewModel(
            service,
            localizationService.GetString,
            new DisplayTextFormatter(localizationService));
        viewModel.SelectedStatus = viewModel.StatusOptions.Single(
            option => option.Value == "RUNNING");

        Assert.AreEqual("运行中", viewModel.SelectedStatus.DisplayText);

        await localizationService.SetLanguageAsync("en-US");
        viewModel.RefreshLocalizedText();

        Assert.AreEqual("RUNNING", viewModel.SelectedStatus.Value);
        Assert.AreEqual("Running", viewModel.SelectedStatus.DisplayText);
    }

    [TestMethod]
    public async Task RetrySelectsNewRunFromOriginalRevision()
    {
        var originalRun = Run("run-original", "FAILED", revisionId: "rev-7");
        var retriedRun = Run(
            "run-retry",
            "PENDING",
            triggerSource: "background_manual",
            revisionId: "rev-7");
        var service = new FakeBackgroundRunService
        {
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success([originalRun]),
            RetryResponse = ApiResponseEnvelope<WorkflowRunDto>.Success(retriedRun),
        };
        var viewModel = CreateViewModel(service);
        await viewModel.LoadPageAsync();
        service.RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
            [retriedRun, originalRun]);

        await viewModel.RetryCommand.ExecuteAsync(null);

        Assert.AreEqual("run-original", service.LastRetriedWorkflowRunId);
        Assert.AreEqual("run-retry", viewModel.SelectedRun?.WorkflowRunId);
        Assert.AreEqual("rev-7", viewModel.SelectedRun?.RevisionId);
    }

    [TestMethod]
    public async Task NonTerminalRunCannotCleanTables()
    {
        var service = new FakeBackgroundRunService
        {
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                [Run("run-running", "RUNNING")]),
        };
        var viewModel = CreateViewModel(service);
        await viewModel.LoadPageAsync();

        Assert.IsFalse(viewModel.CanCleanupSelectedRun);
        Assert.IsFalse(viewModel.CleanupTablesCommand.CanExecute(null));

        await viewModel.CleanupTablesCommand.ExecuteAsync(null);

        Assert.AreEqual(0, service.CleanupCallCount);
    }

    [TestMethod]
    public async Task TerminalRunCleanupPublishesCleanupResult()
    {
        var result = new RunTableCleanupResultDto
        {
            WorkflowRunId = "run-aborted",
            CleanedCount = 2,
            SkippedCount = 1,
        };
        var service = new FakeBackgroundRunService
        {
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                [Run("run-aborted", "ABORTED")]),
            CleanupResponse = ApiResponseEnvelope<RunTableCleanupResultDto>.Success(result),
        };
        var viewModel = CreateViewModel(service);
        await viewModel.LoadPageAsync();
        RunTableCleanupResultDto? published = null;
        viewModel.TablesCleaned += (_, cleanupResult) => published = cleanupResult;

        await viewModel.CleanupTablesCommand.ExecuteAsync(null);

        Assert.AreEqual("run-aborted", service.LastCleanedWorkflowRunId);
        Assert.IsNotNull(published);
        Assert.AreEqual(2, published.CleanedCount);
        Assert.AreEqual(1, published.SkippedCount);
    }

    [TestMethod]
    public async Task TerminalRunCleanupContinuesUntilCompleted()
    {
        var service = new FakeBackgroundRunService
        {
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                [Run("run-complete", "SUCCEEDED")]),
            CleanupBatchHandler = (cursor, _) => Task.FromResult(
                ApiResponseEnvelope<RunTableCleanupResultDto>.Success(
                    cursor is null
                        ? new RunTableCleanupResultDto
                        {
                            WorkflowRunId = "run-complete",
                            Outcome = "RETRY_PENDING",
                            ProcessedCount = 10,
                            CleanedCount = 10,
                            CleanedTableRefIds = Enumerable.Range(0, 10)
                                .Select(index => $"table-{index}")
                                .ToArray(),
                            ContinuationCursor = "cursor-1",
                        }
                        : new RunTableCleanupResultDto
                        {
                            WorkflowRunId = "run-complete",
                            Outcome = "COMPLETED",
                            ProcessedCount = 2,
                            CleanedCount = 1,
                            SkippedCount = 1,
                            CleanedTableRefIds = ["table-10"],
                            Skipped =
                            [
                                new RunTableCleanupIssueDto
                                {
                                    TableRefId = "external-1",
                                    Reason = "external_or_unsupported_storage",
                                },
                            ],
                        })),
        };
        var viewModel = CreateViewModel(service);
        await viewModel.LoadPageAsync();
        RunTableCleanupResultDto? published = null;
        viewModel.TablesCleaned += (_, cleanupResult) => published = cleanupResult;

        await viewModel.CleanupTablesCommand.ExecuteAsync(null);

        Assert.AreEqual(2, service.CleanupCallCount);
        CollectionAssert.AreEqual(
            new string?[] { null, "cursor-1" },
            service.CleanupCursors.ToArray());
        Assert.IsNotNull(published);
        Assert.AreEqual("COMPLETED", published.Outcome);
        Assert.AreEqual(12, published.ProcessedCount);
        Assert.AreEqual(11, published.CleanedCount);
        Assert.AreEqual(1, published.SkippedCount);
        Assert.HasCount(11, published.CleanedTableRefIds);
    }

    [TestMethod]
    public async Task SwitchingRunCancelsCleanupContinuationForOriginalRun()
    {
        var secondBatchStarted = NewCompletionSource();
        CancellationToken secondBatchToken = default;
        var service = new FakeBackgroundRunService
        {
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                [Run("run-first", "SUCCEEDED"), Run("run-second", "SUCCEEDED")]),
            CleanupBatchHandler = async (cursor, cancellationToken) =>
            {
                if (cursor is null)
                {
                    return ApiResponseEnvelope<RunTableCleanupResultDto>.Success(
                        new RunTableCleanupResultDto
                        {
                            WorkflowRunId = "run-first",
                            Outcome = "RETRY_PENDING",
                            ProcessedCount = 1,
                            CleanedCount = 1,
                            CleanedTableRefIds = ["table-1"],
                            ContinuationCursor = "cursor-1",
                        });
                }

                secondBatchToken = cancellationToken;
                secondBatchStarted.SetResult();
                await Task.Delay(Timeout.Infinite, cancellationToken);
                throw new InvalidOperationException();
            },
        };
        var viewModel = CreateViewModel(service);
        await viewModel.LoadPageAsync();
        var publishedRunIds = new List<string>();
        viewModel.TablesCleaned += (runId, _) => publishedRunIds.Add(runId);

        var cleanupTask = viewModel.CleanupTablesCommand.ExecuteAsync(null);
        await secondBatchStarted.Task;
        viewModel.SelectRun(viewModel.Runs[1]);
        await cleanupTask;

        Assert.IsTrue(secondBatchToken.IsCancellationRequested);
        Assert.AreEqual("run-second", viewModel.SelectedRun?.WorkflowRunId);
        CollectionAssert.AreEqual(
            new[] { "run-first" },
            publishedRunIds.ToArray());
        Assert.AreEqual("runs.background.cleanup_cancelled", viewModel.Message);
    }

    [TestMethod]
    public async Task RapidFilterChangeCancelsOldRequestAndIgnoresLateResult()
    {
        var firstStarted = NewCompletionSource();
        var secondStarted = NewCompletionSource();
        var firstResponse = NewRunResponseSource();
        var secondResponse = NewRunResponseSource();
        var firstReturned = NewCompletionSource();
        CancellationToken firstToken = default;
        var service = new FakeBackgroundRunService
        {
            ListHandler = async (request, cancellationToken) =>
            {
                if (request.TriggerSource == "manual")
                {
                    firstToken = cancellationToken;
                    firstStarted.TrySetResult();
                    var response = await firstResponse.Task;
                    firstReturned.TrySetResult();
                    return response;
                }

                secondStarted.TrySetResult();
                return await secondResponse.Task;
            },
        };
        var viewModel = CreateViewModel(service);

        viewModel.SelectedTriggerSource = viewModel.TriggerSourceOptions.Single(
            option => option.Value == "manual");
        await firstStarted.Task.WaitAsync(TimeSpan.FromSeconds(2));
        viewModel.SelectedTriggerSource = viewModel.TriggerSourceOptions.Single(
            option => option.Value == "background_manual");
        await secondStarted.Task.WaitAsync(TimeSpan.FromSeconds(2));

        secondResponse.SetResult(
            ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                [Run("run-current", "RUNNING", "background_manual")]));
        await WaitUntilAsync(
            () => !viewModel.IsLoading &&
                viewModel.Runs.FirstOrDefault()?.WorkflowRunId == "run-current");

        firstResponse.SetResult(
            ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                [Run("run-stale", "SUCCEEDED")]));
        await firstReturned.Task.WaitAsync(TimeSpan.FromSeconds(2));

        Assert.IsTrue(firstToken.IsCancellationRequested);
        Assert.HasCount(1, viewModel.Runs);
        Assert.AreEqual("run-current", viewModel.Runs[0].WorkflowRunId);
    }

    [TestMethod]
    public async Task MergeRunReplacesOnlyMatchingRunAndPreservesSelection()
    {
        var selectedRun = Run("run-selected", "RUNNING");
        var changingRun = Run("run-changing", "RUNNING", "background_manual");
        var service = new FakeBackgroundRunService
        {
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                [selectedRun, changingRun]),
        };
        var viewModel = CreateViewModel(service);
        await viewModel.LoadPageAsync();
        service.GetRunResponse = ApiResponseEnvelope<WorkflowRunDto>.Success(
            changingRun with { Status = "SUCCEEDED" });

        var merged = await viewModel.MergeRunAsync("run-changing");

        Assert.IsTrue(merged);
        Assert.AreEqual("run-selected", viewModel.SelectedRun?.WorkflowRunId);
        Assert.AreEqual(
            "SUCCEEDED",
            viewModel.Runs.Single(run => run.WorkflowRunId == "run-changing").Status);
        Assert.HasCount(2, viewModel.Runs);
    }

    private static BackgroundRunManagementViewModel CreateViewModel(
        FakeBackgroundRunService service)
    {
        var viewModel = new BackgroundRunManagementViewModel(service, key => key);
        viewModel.SetContext(Settings(), "wf-1", canUseActions: true);
        return viewModel;
    }

    private static EngineHostConnectionSettings Settings()
    {
        return new EngineHostConnectionSettings
        {
            BaseUrl = "http://127.0.0.1:8000",
            Token = "secret",
        };
    }

    private static WorkflowRunDto Run(
        string workflowRunId,
        string status,
        string triggerSource = "manual",
        string revisionId = "rev-1")
    {
        return new WorkflowRunDto
        {
            WorkflowRunId = workflowRunId,
            WorkflowId = "wf-1",
            RevisionId = revisionId,
            WorkflowVersion = 1,
            Status = status,
            RunMode = "full",
            TriggerSource = triggerSource,
            StateVersion = 1,
        };
    }

    private static TaskCompletionSource NewCompletionSource()
    {
        return new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
    }

    private static TaskCompletionSource<ApiResponseEnvelope<List<WorkflowRunDto>>>
        NewRunResponseSource()
    {
        return new TaskCompletionSource<ApiResponseEnvelope<List<WorkflowRunDto>>>(
            TaskCreationOptions.RunContinuationsAsynchronously);
    }

    private static async Task WaitUntilAsync(Func<bool> predicate)
    {
        for (var attempt = 0; attempt < 100; attempt++)
        {
            if (predicate())
            {
                return;
            }

            await Task.Delay(10);
        }

        Assert.Fail("The expected asynchronous state was not reached.");
    }

    private sealed record RunListRequest(
        string? WorkflowId,
        IReadOnlyCollection<string>? Statuses,
        string? RunMode,
        string? TriggerSource,
        int Offset,
        int Limit);

    private sealed class FakeBackgroundRunService : IBackgroundRunService
    {
        public ApiResponseEnvelope<WorkflowRunDto> StartResponse { get; set; } =
            ApiResponseEnvelope<WorkflowRunDto>.Failure("NOT_CONFIGURED", "No start response.");

        public ApiResponseEnvelope<List<WorkflowRunDto>> RunsResponse { get; set; } =
            ApiResponseEnvelope<List<WorkflowRunDto>>.Success([]);

        public ApiResponseEnvelope<WorkflowRunDto> RetryResponse { get; set; } =
            ApiResponseEnvelope<WorkflowRunDto>.Failure("NOT_CONFIGURED", "No retry response.");

        public ApiResponseEnvelope<WorkflowRunDto> GetRunResponse { get; set; } =
            ApiResponseEnvelope<WorkflowRunDto>.Failure("NOT_CONFIGURED", "No run response.");

        public ApiResponseEnvelope<RunTableCleanupResultDto> CleanupResponse { get; set; } =
            ApiResponseEnvelope<RunTableCleanupResultDto>.Failure(
                "NOT_CONFIGURED",
                "No cleanup response.");

        public Func<
            RunListRequest,
            CancellationToken,
            Task<ApiResponseEnvelope<List<WorkflowRunDto>>>>? ListHandler { get; set; }

        public Func<
            string?,
            CancellationToken,
            Task<ApiResponseEnvelope<RunTableCleanupResultDto>>>?
            CleanupBatchHandler { get; set; }

        public string? LastStartedWorkflowId { get; private set; }

        public string? LastStartedRunMode { get; private set; }

        public RunListRequest? LastListRequest { get; private set; }

        public string? LastRetriedWorkflowRunId { get; private set; }

        public string? LastCleanedWorkflowRunId { get; private set; }

        public int CleanupCallCount { get; private set; }

        public List<string?> CleanupCursors { get; } = [];

        public Task<ApiResponseEnvelope<WorkflowRunDto>> StartAsync(
            EngineHostConnectionSettings settings,
            string workflowId,
            string runMode = "full",
            string? targetNodeInstanceId = null,
            CancellationToken cancellationToken = default)
        {
            LastStartedWorkflowId = workflowId;
            LastStartedRunMode = runMode;
            return Task.FromResult(StartResponse);
        }

        public Task<ApiResponseEnvelope<List<WorkflowRunDto>>> ListRunsAsync(
            EngineHostConnectionSettings settings,
            string? workflowId = null,
            IReadOnlyCollection<string>? statuses = null,
            string? runMode = null,
            string? triggerSource = null,
            int offset = 0,
            int limit = 100,
            CancellationToken cancellationToken = default)
        {
            LastListRequest = new RunListRequest(
                workflowId,
                statuses,
                runMode,
                triggerSource,
                offset,
                limit);
            return ListHandler is null
                ? Task.FromResult(RunsResponse)
                : ListHandler(LastListRequest, cancellationToken);
        }

        public Task<ApiResponseEnvelope<WorkflowProcessDto>> CancelAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<WorkflowProcessDto>.Failure(
                    "NOT_CONFIGURED",
                    "No cancel response."));
        }

        public Task<ApiResponseEnvelope<WorkflowRunDto>> GetRunAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(GetRunResponse);
        }

        public Task<ApiResponseEnvelope<WorkflowRunDto>> RetryAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            string? triggerSource = null,
            CancellationToken cancellationToken = default)
        {
            LastRetriedWorkflowRunId = workflowRunId;
            return Task.FromResult(RetryResponse);
        }

        public Task<ApiResponseEnvelope<RunTableCleanupResultDto>> CleanupTablesAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            CleanupCallCount++;
            LastCleanedWorkflowRunId = workflowRunId;
            return Task.FromResult(CleanupResponse);
        }

        public Task<ApiResponseEnvelope<RunTableCleanupResultDto>> CleanupTablesBatchAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            int maxRefs,
            int timeBudgetMs,
            string? cursor = null,
            CancellationToken cancellationToken = default)
        {
            CleanupCallCount++;
            LastCleanedWorkflowRunId = workflowRunId;
            CleanupCursors.Add(cursor);
            return CleanupBatchHandler is null
                ? Task.FromResult(CleanupResponse)
                : CleanupBatchHandler(cursor, cancellationToken);
        }
    }
}
