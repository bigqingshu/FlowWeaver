using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;
using Avalonia_UI.Models;
using Avalonia_UI.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public sealed partial class WorkflowRunRuntimeOptionsViewModel : ViewModelBase
{
    private const string VersionConflictError = "RUNTIME_OPTIONS_VERSION_CONFLICT";
    private const string InactiveRunError = "RUNTIME_OPTIONS_RUN_NOT_ACTIVE";

    private static readonly JsonSerializerOptions DisplayJsonOptions = new(FlowWeaverJson.Options)
    {
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        WriteIndented = true,
    };

    private readonly IWorkflowRunRuntimeOptionsService service;
    private readonly EngineHostConnectionSettings settings;
    private readonly ILocalizationService localizationService;

    [ObservableProperty]
    private RuntimeFeedbackPolicyOverrideEditorViewModel workflowEditor;

    [ObservableProperty]
    private WorkflowRunRuntimeOptionsNodeViewModel? selectedNode;

    [ObservableProperty]
    private bool isBusy;

    [ObservableProperty]
    private bool isLoaded;

    [ObservableProperty]
    private bool isReadOnly;

    [ObservableProperty]
    private bool hasOverlay;

    [ObservableProperty]
    private string runStatus;

    [ObservableProperty]
    private int requestedVersion;

    [ObservableProperty]
    private int appliedVersion;

    [ObservableProperty]
    private DateTimeOffset? requestedAt;

    [ObservableProperty]
    private DateTimeOffset? appliedAt;

    [ObservableProperty]
    private string savedRuntimeOptionsJson = "{}";

    [ObservableProperty]
    private string overlayJson = "{}";

    [ObservableProperty]
    private string effectiveWorkflowSummaryText = string.Empty;

    [ObservableProperty]
    private string applicationStatusText = string.Empty;

    [ObservableProperty]
    private string statusMessage = string.Empty;

    [ObservableProperty]
    private string? errorMessage;

    public WorkflowRunRuntimeOptionsViewModel(
        IWorkflowRunRuntimeOptionsService service,
        EngineHostConnectionSettings settings,
        string workflowRunId,
        string runStatus,
        string runMode,
        string triggerSource,
        ILocalizationService localizationService)
    {
        this.service = service;
        this.settings = settings;
        this.localizationService = localizationService;
        WorkflowRunId = workflowRunId;
        this.runStatus = runStatus;
        RunMode = runMode;
        TriggerSource = triggerSource;
        isReadOnly = !IsEditableRunStatus(runStatus);
        workflowEditor = new RuntimeFeedbackPolicyOverrideEditorViewModel(
            localizationService);
        StatusMessage = T("run_runtime_options.loading");
    }

    public string WorkflowRunId { get; }

    public string RunMode { get; }

    public string TriggerSource { get; }

    public ObservableCollection<WorkflowRunRuntimeOptionsNodeViewModel> Nodes { get; } = new();

    public ObservableCollection<WorkflowRunRuntimeOptionsTaskViewModel> ActiveTasks { get; } = new();

    public bool CanEdit => IsLoaded && !IsReadOnly && !IsBusy;

    public bool ShowEditActions => !IsReadOnly;

    public bool HasError => !string.IsNullOrWhiteSpace(ErrorMessage);

    public bool HasSelectedNode => SelectedNode is not null;

    public bool HasActiveTasks => ActiveTasks.Count > 0;

    public string WindowTitleText => T("run_runtime_options.window_title");

    public string RunIdentityText => localizationService.Format(
        "run_runtime_options.run_identity_format",
        WorkflowRunId,
        RunStatus,
        RunMode,
        TriggerSource);

    public string VersionsText => localizationService.Format(
        "run_runtime_options.versions_format",
        RequestedVersion,
        AppliedVersion);

    public string RequestedAtText => FormatTimestamp(RequestedAt);

    public string AppliedAtText => FormatTimestamp(AppliedAt);

    public string ApplicationTimesText => localizationService.Format(
        "run_runtime_options.application_times_format",
        RequestedAtText,
        AppliedAtText);

    public string OverlayTabText => T("run_runtime_options.tab.overlay");

    public string EffectiveTabText => T("run_runtime_options.tab.effective");

    public string ActiveTasksTabText => T("run_runtime_options.tab.active_tasks");

    public string WorkflowOverrideText => T("run_runtime_options.workflow_override");

    public string NodeOverrideText => T("run_runtime_options.node_override");

    public string SelectNodeText => T("definition.runtime_options_select_node");

    public string RevisionOptionsText => T("run_runtime_options.revision_options");

    public string CurrentOverlayText => T("run_runtime_options.current_overlay");

    public string EffectiveWorkflowText => T("run_runtime_options.effective_workflow");

    public string EffectiveNodeText => T("run_runtime_options.effective_node");

    public string RefreshText => T("common.refresh");

    public string SaveText => T("run_runtime_options.save");

    public string ClearText => T("run_runtime_options.clear");

    public string CloseText => T("common.close");

    public string ReadOnlyText => T("run_runtime_options.read_only");

    public string NoActiveTasksText => T("run_runtime_options.no_active_tasks");

    public string TaskNodeText => T("run_runtime_options.task.node");

    public string TaskStatusText => T("run_runtime_options.task.status");

    public string TaskVersionText => T("run_runtime_options.task.version");

    public async Task LoadAsync()
    {
        if (IsBusy)
        {
            return;
        }

        IsBusy = true;
        ErrorMessage = null;
        StatusMessage = T("run_runtime_options.loading");
        try
        {
            var response = await service.GetAsync(settings, WorkflowRunId);
            if (response.Ok && response.Data is not null)
            {
                ApplyState(response.Data);
                StatusMessage = T("run_runtime_options.loaded");
                return;
            }

            ErrorMessage = FormatApiError(response.Error, "run_runtime_options.load_failed");
            StatusMessage = T("run_runtime_options.load_failed");
        }
        finally
        {
            IsBusy = false;
        }
    }

    [RelayCommand]
    private Task RefreshAsync() => LoadAsync();

    [RelayCommand(CanExecute = nameof(CanSave))]
    private async Task SaveAsync()
    {
        if (!TryBuildOverlay(out var overlay))
        {
            return;
        }

        await ReplaceAsync(overlay, "run_runtime_options.saved");
    }

    [RelayCommand(CanExecute = nameof(CanClear))]
    private Task ClearAsync()
    {
        return ReplaceAsync(
            new WorkflowRunRuntimeOptionsOverlayDto(),
            "run_runtime_options.cleared");
    }

    private bool CanSave() => CanEdit;

    private bool CanClear() => CanEdit && HasOverlay;

    private async Task ReplaceAsync(
        WorkflowRunRuntimeOptionsOverlayDto overlay,
        string successMessageKey)
    {
        IsBusy = true;
        ErrorMessage = null;
        StatusMessage = T("run_runtime_options.saving");
        try
        {
            var response = await service.ReplaceAsync(
                settings,
                WorkflowRunId,
                RequestedVersion,
                overlay);
            if (response.Ok && response.Data is not null)
            {
                ApplyState(response.Data);
                StatusMessage = T(successMessageKey);
                return;
            }

            if (response.Error?.ErrorCode == VersionConflictError)
            {
                await ReloadAfterConflictAsync();
                ErrorMessage = T("run_runtime_options.version_conflict");
                StatusMessage = T("run_runtime_options.version_conflict");
                return;
            }

            if (response.Error?.ErrorCode == InactiveRunError)
            {
                ApplyInactiveRunStatus(response.Error);
            }

            ErrorMessage = FormatApiError(response.Error, "run_runtime_options.save_failed");
            StatusMessage = T("run_runtime_options.save_failed");
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task ReloadAfterConflictAsync()
    {
        var latest = await service.GetAsync(settings, WorkflowRunId);
        if (latest.Ok && latest.Data is not null)
        {
            ApplyState(latest.Data);
        }
    }

    private bool TryBuildOverlay(out WorkflowRunRuntimeOptionsOverlayDto overlay)
    {
        if (!WorkflowEditor.TryBuild(out var workflowDraft, out var validationError))
        {
            ErrorMessage = validationError;
            overlay = new WorkflowRunRuntimeOptionsOverlayDto();
            return false;
        }

        var nodeDrafts = new Dictionary<string, RuntimeFeedbackPolicyOverrideDraft>(
            StringComparer.Ordinal);
        foreach (var node in Nodes)
        {
            if (!node.Editor.TryBuild(out var nodeDraft, out validationError))
            {
                ErrorMessage = localizationService.Format(
                    "run_runtime_options.node_validation_failed_format",
                    node.NodeInstanceId,
                    validationError);
                overlay = new WorkflowRunRuntimeOptionsOverlayDto();
                return false;
            }

            if (!nodeDraft.IsEmpty)
            {
                nodeDrafts[node.NodeInstanceId] = nodeDraft;
            }
        }

        overlay = WorkflowRunRuntimeOptionsDraftMapper.ToDto(
            new WorkflowRunRuntimeOptionsDraft
            {
                Workflow = workflowDraft,
                NodeOverrides = nodeDrafts,
            });
        return true;
    }

    private void ApplyState(WorkflowRunRuntimeOptionsDto state)
    {
        var selectedNodeId = SelectedNode?.NodeInstanceId;
        RequestedVersion = state.RequestedVersion;
        AppliedVersion = state.AppliedVersion;
        RequestedAt = state.RequestedAt;
        AppliedAt = state.AppliedAt;
        HasOverlay = state.Overlay.Workflow is not null || state.Overlay.NodeOverrides.Count > 0;
        SavedRuntimeOptionsJson = FormatJson(state.SavedRuntimeOptions);
        OverlayJson = JsonSerializer.Serialize(state.Overlay, DisplayJsonOptions);
        EffectiveWorkflowSummaryText = WorkflowRunRuntimeOptionsNodeViewModel.FormatPolicy(
            state.EffectiveSummary.Workflow,
            localizationService);
        ApplicationStatusText = ApplicationStateText(
            WorkflowRunRuntimeOptionsApplicationStateResolver.Resolve(state));

        var draft = WorkflowRunRuntimeOptionsDraftMapper.FromDto(state.Overlay);
        WorkflowEditor = new RuntimeFeedbackPolicyOverrideEditorViewModel(
            localizationService,
            draft.Workflow);

        ActiveTasks.Clear();
        foreach (var task in state.ActiveTaskVersions.OrderBy(task => task.NodeInstanceId, StringComparer.Ordinal))
        {
            ActiveTasks.Add(new WorkflowRunRuntimeOptionsTaskViewModel(
                task,
                state.RequestedVersion,
                localizationService));
        }

        Nodes.Clear();
        foreach (var item in state.EffectiveSummary.Nodes.OrderBy(item => item.Key, StringComparer.Ordinal))
        {
            draft.NodeOverrides.TryGetValue(item.Key, out var nodeDraft);
            Nodes.Add(new WorkflowRunRuntimeOptionsNodeViewModel(
                item.Key,
                item.Value,
                nodeDraft ?? new RuntimeFeedbackPolicyOverrideDraft(),
                state.ActiveTaskVersions
                    .Where(task => string.Equals(task.NodeInstanceId, item.Key, StringComparison.Ordinal))
                    .ToArray(),
                state.RequestedVersion,
                localizationService));
        }

        SelectedNode = Nodes.FirstOrDefault(
            node => string.Equals(node.NodeInstanceId, selectedNodeId, StringComparison.Ordinal))
            ?? Nodes.FirstOrDefault();
        IsLoaded = true;
        OnPropertyChanged(nameof(HasActiveTasks));
        OnPropertyChanged(nameof(VersionsText));
        OnPropertyChanged(nameof(RequestedAtText));
        OnPropertyChanged(nameof(AppliedAtText));
    }

    private string ApplicationStateText(WorkflowRunRuntimeOptionsApplicationState state)
    {
        return state switch
        {
            WorkflowRunRuntimeOptionsApplicationState.MainProgramPending =>
                T("run_runtime_options.state.main_pending"),
            WorkflowRunRuntimeOptionsApplicationState.ActiveNodesPending =>
                T("run_runtime_options.state.nodes_pending"),
            _ => T("run_runtime_options.state.applied"),
        };
    }

    private void ApplyInactiveRunStatus(ApiErrorDto error)
    {
        if (error.Details.ValueKind == JsonValueKind.Object
            && error.Details.TryGetProperty("status", out var status)
            && !string.IsNullOrWhiteSpace(status.GetString()))
        {
            RunStatus = status.GetString()!;
        }

        IsReadOnly = true;
    }

    private string FormatApiError(ApiErrorDto? error, string fallbackKey)
    {
        return error is null || string.IsNullOrWhiteSpace(error.Message)
            ? T(fallbackKey)
            : $"{T(fallbackKey)} {error.Message}";
    }

    private static string FormatJson(JsonElement value)
    {
        return value.ValueKind is JsonValueKind.Undefined or JsonValueKind.Null
            ? "{}"
            : JsonSerializer.Serialize(value, DisplayJsonOptions);
    }

    private static bool IsEditableRunStatus(string status)
    {
        return status is "PENDING" or "RUNNING";
    }

    private static string FormatTimestamp(DateTimeOffset? value)
    {
        return value?.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss") ?? "-";
    }

    private string T(string key) => localizationService.GetString(key);

    partial void OnSelectedNodeChanged(WorkflowRunRuntimeOptionsNodeViewModel? value)
    {
        OnPropertyChanged(nameof(HasSelectedNode));
    }

    partial void OnErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasError));
    }

    partial void OnRequestedVersionChanged(int value)
    {
        OnPropertyChanged(nameof(VersionsText));
    }

    partial void OnAppliedVersionChanged(int value)
    {
        OnPropertyChanged(nameof(VersionsText));
    }

    partial void OnRequestedAtChanged(DateTimeOffset? value)
    {
        OnPropertyChanged(nameof(RequestedAtText));
        OnPropertyChanged(nameof(ApplicationTimesText));
    }

    partial void OnAppliedAtChanged(DateTimeOffset? value)
    {
        OnPropertyChanged(nameof(AppliedAtText));
        OnPropertyChanged(nameof(ApplicationTimesText));
    }

    partial void OnRunStatusChanged(string value)
    {
        OnPropertyChanged(nameof(RunIdentityText));
    }

    partial void OnIsBusyChanged(bool value) => NotifyCommandStateChanged();

    partial void OnIsLoadedChanged(bool value) => NotifyCommandStateChanged();

    partial void OnIsReadOnlyChanged(bool value)
    {
        OnPropertyChanged(nameof(CanEdit));
        OnPropertyChanged(nameof(ShowEditActions));
        NotifyCommandStateChanged();
    }

    partial void OnHasOverlayChanged(bool value) => NotifyCommandStateChanged();

    private void NotifyCommandStateChanged()
    {
        OnPropertyChanged(nameof(CanEdit));
        SaveCommand.NotifyCanExecuteChanged();
        ClearCommand.NotifyCanExecuteChanged();
    }
}
