using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Text.Json;
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
public sealed class WorkflowRunRuntimeOptionsViewModelTests
{
    [TestMethod]
    public async Task LoadDistinguishesMainNodeAndFullyAppliedStates()
    {
        var service = new FakeRuntimeOptionsService();
        service.GetResponses.Enqueue(SuccessState(requestedVersion: 2, appliedVersion: 1, taskVersion: 1));
        service.GetResponses.Enqueue(SuccessState(requestedVersion: 2, appliedVersion: 2, taskVersion: 1));
        service.GetResponses.Enqueue(SuccessState(requestedVersion: 2, appliedVersion: 2, taskVersion: 2));
        var viewModel = CreateViewModel(service);

        await viewModel.LoadAsync();
        Assert.AreEqual(
            Localization().GetString("run_runtime_options.state.main_pending"),
            viewModel.ApplicationStatusText);

        await viewModel.LoadAsync();
        Assert.AreEqual(
            Localization().GetString("run_runtime_options.state.nodes_pending"),
            viewModel.ApplicationStatusText);

        await viewModel.LoadAsync();
        Assert.AreEqual(
            Localization().GetString("run_runtime_options.state.applied"),
            viewModel.ApplicationStatusText);
        Assert.AreEqual(2, viewModel.RequestedVersion);
        Assert.AreEqual(2, viewModel.AppliedVersion);
        Assert.HasCount(1, viewModel.ActiveTasks);
        Assert.IsTrue(viewModel.ActiveTasks[0].IsApplied);
    }

    [TestMethod]
    public async Task SaveBuildsWorkflowAndNodeOverlayWithoutWorkflowDraftMutation()
    {
        var service = new FakeRuntimeOptionsService();
        service.GetResponses.Enqueue(SuccessState(requestedVersion: 0, appliedVersion: 0));
        service.ReplaceResponses.Enqueue(SuccessState(
            requestedVersion: 1,
            appliedVersion: 0,
            overlay: new WorkflowRunRuntimeOptionsOverlayDto
            {
                Workflow = PolicyOverride(logLevel: "WARN", progressEnabled: false),
                NodeOverrides = new()
                {
                    ["source"] = PolicyOverride(logLevel: "DEBUG"),
                },
            }));
        var viewModel = CreateViewModel(service);
        await viewModel.LoadAsync();
        viewModel.WorkflowEditor.SelectedLogLevel = viewModel.WorkflowEditor.LogLevelOptions
            .First(option => option.Value == "WARN");
        viewModel.WorkflowEditor.ProgressEnabled = false;
        Assert.IsNotNull(viewModel.SelectedNode);
        viewModel.SelectedNode!.Editor.SelectedLogLevel = viewModel.SelectedNode.Editor.LogLevelOptions
            .First(option => option.Value == "DEBUG");

        await viewModel.SaveCommand.ExecuteAsync(null);

        Assert.AreEqual(0, service.LastExpectedVersion);
        Assert.IsNotNull(service.LastOverlay?.Workflow);
        Assert.AreEqual("WARN", service.LastOverlay.Workflow.Telemetry?.LogLevel);
        Assert.IsFalse(service.LastOverlay.Workflow.Telemetry?.ProgressEnabled);
        Assert.AreEqual(
            "DEBUG",
            service.LastOverlay.NodeOverrides["source"].Telemetry?.LogLevel);
        Assert.AreEqual(1, viewModel.RequestedVersion);
        Assert.IsTrue(viewModel.HasOverlay);
    }

    [TestMethod]
    public async Task VersionConflictRefreshesLatestStateBeforeResubmit()
    {
        var service = new FakeRuntimeOptionsService();
        service.GetResponses.Enqueue(SuccessState(requestedVersion: 1, appliedVersion: 1));
        service.GetResponses.Enqueue(SuccessState(
            requestedVersion: 2,
            appliedVersion: 2,
            overlay: new WorkflowRunRuntimeOptionsOverlayDto
            {
                Workflow = PolicyOverride(logLevel: "ERROR"),
            }));
        service.ReplaceResponses.Enqueue(
            ApiResponseEnvelope<WorkflowRunRuntimeOptionsDto>.Failure(
                "RUNTIME_OPTIONS_VERSION_CONFLICT",
                "version conflict"));
        var viewModel = CreateViewModel(service);
        await viewModel.LoadAsync();
        viewModel.WorkflowEditor.SelectedLogLevel = viewModel.WorkflowEditor.LogLevelOptions
            .First(option => option.Value == "WARN");

        await viewModel.SaveCommand.ExecuteAsync(null);

        Assert.AreEqual(1, service.LastExpectedVersion);
        Assert.AreEqual(2, service.GetCallCount);
        Assert.AreEqual(2, viewModel.RequestedVersion);
        Assert.AreEqual("ERROR", viewModel.WorkflowEditor.SelectedLogLevel?.Value);
        Assert.AreEqual(
            Localization().GetString("run_runtime_options.version_conflict"),
            viewModel.ErrorMessage);
        Assert.IsTrue(viewModel.SaveCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task ClearSendsEmptyOverlayAtCurrentVersion()
    {
        var service = new FakeRuntimeOptionsService();
        service.GetResponses.Enqueue(SuccessState(
            requestedVersion: 3,
            appliedVersion: 3,
            overlay: new WorkflowRunRuntimeOptionsOverlayDto
            {
                Workflow = PolicyOverride(logLevel: "WARN"),
            }));
        service.ReplaceResponses.Enqueue(SuccessState(requestedVersion: 4, appliedVersion: 3));
        var viewModel = CreateViewModel(service);
        await viewModel.LoadAsync();

        await viewModel.ClearCommand.ExecuteAsync(null);

        Assert.AreEqual(3, service.LastExpectedVersion);
        Assert.IsNull(service.LastOverlay?.Workflow);
        Assert.AreEqual(0, service.LastOverlay?.NodeOverrides.Count);
        Assert.IsFalse(viewModel.HasOverlay);
    }

    [TestMethod]
    public async Task TerminalRunLoadsReadOnlyAndHidesExecutableCommands()
    {
        var service = new FakeRuntimeOptionsService();
        service.GetResponses.Enqueue(SuccessState(requestedVersion: 2, appliedVersion: 2));
        var viewModel = CreateViewModel(service, runStatus: "SUCCEEDED");

        await viewModel.LoadAsync();

        Assert.IsTrue(viewModel.IsReadOnly);
        Assert.IsFalse(viewModel.CanEdit);
        Assert.IsFalse(viewModel.SaveCommand.CanExecute(null));
        Assert.IsFalse(viewModel.ClearCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task InactiveRunResponseSwitchesOpenEditorToReadOnly()
    {
        var service = new FakeRuntimeOptionsService();
        service.GetResponses.Enqueue(SuccessState(requestedVersion: 1, appliedVersion: 1));
        using var details = JsonDocument.Parse("{\"status\":\"CANCEL_REQUESTED\"}");
        service.ReplaceResponses.Enqueue(
            ApiResponseEnvelope<WorkflowRunRuntimeOptionsDto>.Failure(
                "RUNTIME_OPTIONS_RUN_NOT_ACTIVE",
                "read only",
                details: details.RootElement.Clone()));
        var viewModel = CreateViewModel(service);
        await viewModel.LoadAsync();

        await viewModel.SaveCommand.ExecuteAsync(null);

        Assert.AreEqual("CANCEL_REQUESTED", viewModel.RunStatus);
        Assert.IsTrue(viewModel.IsReadOnly);
        Assert.IsFalse(viewModel.ShowEditActions);
        Assert.IsFalse(viewModel.SaveCommand.CanExecute(null));
    }

    [TestMethod]
    public void DraftMapperPreservesExplicitEmptyRedactColumnsOverride()
    {
        var overlay = new WorkflowRunRuntimeOptionsOverlayDto
        {
            Workflow = new RuntimeFeedbackPolicyOverrideDto
            {
                Diagnostics = new RuntimeFeedbackDiagnosticsOverrideDto
                {
                    RedactColumns = new(),
                },
            },
        };

        var roundTrip = WorkflowRunRuntimeOptionsDraftMapper.ToDto(
            WorkflowRunRuntimeOptionsDraftMapper.FromDto(overlay));

        Assert.IsNotNull(roundTrip.Workflow?.Diagnostics?.RedactColumns);
        Assert.HasCount(0, roundTrip.Workflow.Diagnostics.RedactColumns);
    }

    [TestMethod]
    public void OverrideEditorTreatsNullRedactColumnsAsExplicitEmptyOverride()
    {
        var editor = new RuntimeFeedbackPolicyOverrideEditorViewModel(Localization())
        {
            OverrideRedactColumns = true,
            RedactColumnsDraft = null!,
        };

        Assert.IsTrue(editor.TryBuild(out var draft, out var validationError));
        Assert.IsNull(validationError);
        Assert.IsNotNull(draft.RedactColumns);
        Assert.HasCount(0, draft.RedactColumns);
    }

    [TestMethod]
    public void MainWindowBridgeSupportsOrdinaryPreviewAndBackgroundRunsWithoutDirtyingDraft()
    {
        var apiClient = new EngineHostApiClient(new HttpClient(new NeverSendHandler()));
        var mainViewModel = new MainWindowViewModel(apiClient)
        {
            ConnectionStatus = ConnectionStatus.Connected,
            Token = "secret",
            WorkflowDefinitionDraftJson = "{\"schema_version\":\"1.0\",\"nodes\":[],\"connections\":[]}",
        };
        var originalDraft = mainViewModel.WorkflowDefinitionDraftJson;
        var runs = new[]
        {
            Run("run-ordinary", "full", "manual"),
            Run("run-preview", "preview_to_node", "manual"),
            Run("run-background", "full", "background_manual"),
        };

        foreach (var run in runs)
        {
            mainViewModel.SelectedRun = new WorkflowRunListItemViewModel(run);
            var editor = mainViewModel.CreateSelectedRunRuntimeOptionsViewModel();

            Assert.IsNotNull(editor);
            Assert.AreEqual(run.WorkflowRunId, editor.WorkflowRunId);
            Assert.AreEqual(run.RunMode, editor.RunMode);
            Assert.AreEqual(run.TriggerSource, editor.TriggerSource);
            Assert.AreEqual(originalDraft, mainViewModel.WorkflowDefinitionDraftJson);
        }
    }

    private static WorkflowRunRuntimeOptionsViewModel CreateViewModel(
        IWorkflowRunRuntimeOptionsService service,
        string runStatus = "RUNNING")
    {
        return new WorkflowRunRuntimeOptionsViewModel(
            service,
            new EngineHostConnectionSettings { Token = "secret" },
            "run-1",
            runStatus,
            "full",
            "manual",
            Localization());
    }

    private static ApiResponseEnvelope<WorkflowRunRuntimeOptionsDto> SuccessState(
        int requestedVersion,
        int appliedVersion,
        int? taskVersion = null,
        WorkflowRunRuntimeOptionsOverlayDto? overlay = null)
    {
        var tasks = taskVersion.HasValue
            ? new List<ActiveNodeTaskRuntimeOptionsVersionDto>
            {
                new()
                {
                    TaskId = "task-1",
                    NodeRunId = "node-run-1",
                    NodeInstanceId = "source",
                    NodeRunStatus = "RUNNING",
                    RuntimeOptionsVersion = taskVersion.Value,
                },
            }
            : new List<ActiveNodeTaskRuntimeOptionsVersionDto>();
        return ApiResponseEnvelope<WorkflowRunRuntimeOptionsDto>.Success(
            new WorkflowRunRuntimeOptionsDto
            {
                WorkflowRunId = "run-1",
                SavedRuntimeOptions = JsonElement("{}"),
                Overlay = overlay ?? new WorkflowRunRuntimeOptionsOverlayDto(),
                EffectiveSummary = new WorkflowRunRuntimeOptionsEffectiveSummaryDto
                {
                    Workflow = ResolvedPolicy(),
                    Nodes = new()
                    {
                        ["source"] = ResolvedPolicy(),
                    },
                },
                RequestedVersion = requestedVersion,
                AppliedVersion = appliedVersion,
                ActiveTaskVersions = tasks,
            });
    }

    private static RuntimeFeedbackPolicyOverrideDto PolicyOverride(
        string? logLevel = null,
        bool? progressEnabled = null)
    {
        return new RuntimeFeedbackPolicyOverrideDto
        {
            Telemetry = new RuntimeFeedbackTelemetryOverrideDto
            {
                LogLevel = logLevel,
                ProgressEnabled = progressEnabled,
            },
        };
    }

    private static ResolvedRuntimeFeedbackPolicyDto ResolvedPolicy()
    {
        return new ResolvedRuntimeFeedbackPolicyDto
        {
            Telemetry = new ResolvedRuntimeFeedbackTelemetryDto
            {
                LogLevel = "INFO",
                EventLevel = "progress",
                EventRateLimitPerSecond = 0,
                ProgressEnabled = true,
                ProgressIntervalSeconds = 0,
            },
            Diagnostics = new ResolvedRuntimeFeedbackDiagnosticsDto
            {
                CaptureErrorContext = true,
                IncludeMetrics = true,
                PayloadByteLimit = 0,
                RedactColumns = new(),
                MaskPolicy = "none",
            },
        };
    }

    private static WorkflowRunDto Run(
        string runId,
        string runMode,
        string triggerSource)
    {
        return new WorkflowRunDto
        {
            WorkflowRunId = runId,
            WorkflowId = "workflow-1",
            RevisionId = "revision-1",
            WorkflowVersion = 1,
            Status = "RUNNING",
            RunMode = runMode,
            TriggerSource = triggerSource,
        };
    }

    private static JsonElement JsonElement(string json)
    {
        using var document = JsonDocument.Parse(json);
        return document.RootElement.Clone();
    }

    private static string LocalizationDirectory()
    {
        return Path.Combine(AppContext.BaseDirectory, "Localization");
    }

    private static JsonLocalizationService Localization()
    {
        return new JsonLocalizationService(LocalizationDirectory());
    }

    private sealed class FakeRuntimeOptionsService : IWorkflowRunRuntimeOptionsService
    {
        public Queue<ApiResponseEnvelope<WorkflowRunRuntimeOptionsDto>> GetResponses { get; } = new();

        public Queue<ApiResponseEnvelope<WorkflowRunRuntimeOptionsDto>> ReplaceResponses { get; } = new();

        public int GetCallCount { get; private set; }

        public int? LastExpectedVersion { get; private set; }

        public WorkflowRunRuntimeOptionsOverlayDto? LastOverlay { get; private set; }

        public Task<ApiResponseEnvelope<WorkflowRunRuntimeOptionsDto>> GetAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            GetCallCount++;
            return Task.FromResult(GetResponses.Dequeue());
        }

        public Task<ApiResponseEnvelope<WorkflowRunRuntimeOptionsDto>> ReplaceAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            int expectedVersion,
            WorkflowRunRuntimeOptionsOverlayDto overlay,
            CancellationToken cancellationToken = default)
        {
            LastExpectedVersion = expectedVersion;
            LastOverlay = overlay;
            return Task.FromResult(ReplaceResponses.Dequeue());
        }
    }

    private sealed class NeverSendHandler : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            throw new InvalidOperationException("The bridge must not issue an API request.");
        }
    }
}
