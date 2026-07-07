using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Linq;
using System.Text.Json;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private static readonly string[] RuntimeOptionsProfileValues =
        ["normal", "background_fast", "diagnostic", "custom"];
    private static readonly string[] RuntimeOptionsLogLevelValues =
        ["DEBUG", "INFO", "WARN", "ERROR"];
    private static readonly string[] RuntimeOptionsEventLevelValues =
        ["none", "basic", "progress", "verbose"];
    private static readonly string[] RuntimeOptionsMaskPolicyValues =
        ["none", "partial", "full"];

    [ObservableProperty]
    private string runtimeOptionsProfileDraft = RuntimeOptionsDefaults.Profile;

    [ObservableProperty]
    private bool runtimeOptionsStrictValidationDraft = true;

    [ObservableProperty]
    private string runtimeOptionsLogLevelDraft = RuntimeOptionsDefaults.LogLevel;

    [ObservableProperty]
    private string runtimeOptionsEventLevelDraft = RuntimeOptionsDefaults.EventLevel;

    [ObservableProperty]
    private string runtimeOptionsEventRateLimitPerSecondDraft = "0";

    [ObservableProperty]
    private bool runtimeOptionsProgressEnabledDraft = true;

    [ObservableProperty]
    private string runtimeOptionsProgressIntervalSecondsDraft = "0";

    [ObservableProperty]
    private bool runtimeOptionsCaptureErrorContextDraft = true;

    [ObservableProperty]
    private bool runtimeOptionsIncludeMetricsDraft = true;

    [ObservableProperty]
    private string runtimeOptionsPayloadByteLimitDraft = "0";

    [ObservableProperty]
    private string runtimeOptionsTtlSecondsDraft = "0";

    [ObservableProperty]
    private string runtimeOptionsRedactColumnsDraft = string.Empty;

    [ObservableProperty]
    private string runtimeOptionsMaskPolicyDraft = RuntimeOptionsDefaults.MaskPolicy;

    [ObservableProperty]
    private WorkflowDefinitionNodeListItemViewModel? selectedRuntimeOptionsNode;

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeProfileDraft = RuntimeOptionsDefaults.Profile;

    [ObservableProperty]
    private bool runtimeOptionsSelectedNodeStrictValidationDraft = true;

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeLogLevelDraft =
        RuntimeOptionsDefaults.LogLevel;

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeEventLevelDraft =
        RuntimeOptionsDefaults.EventLevel;

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeEventRateLimitPerSecondDraft = "0";

    [ObservableProperty]
    private bool runtimeOptionsSelectedNodeProgressEnabledDraft = true;

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeProgressIntervalSecondsDraft = "0";

    [ObservableProperty]
    private bool runtimeOptionsSelectedNodeCaptureErrorContextDraft = true;

    [ObservableProperty]
    private bool runtimeOptionsSelectedNodeIncludeMetricsDraft = true;

    [ObservableProperty]
    private string runtimeOptionsSelectedNodePayloadByteLimitDraft = "0";

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeTtlSecondsDraft = "0";

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeRedactColumnsDraft = string.Empty;

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeMaskPolicyDraft =
        RuntimeOptionsDefaults.MaskPolicy;

    [ObservableProperty]
    private int runtimeOptionsNodeOverrideCount;

    [ObservableProperty]
    private string? runtimeOptionsEditorErrorMessage;

    [ObservableProperty]
    private bool isRuntimeOptionsJsonEditorExpanded;

    [ObservableProperty]
    private string runtimeOptionsJsonDraft = string.Empty;

    [ObservableProperty]
    private bool isRuntimeOptionsJsonDraftDirty;

    private bool isSynchronizingRuntimeOptionsJsonDraft;

    public IReadOnlyList<NodeConfigOptionItemViewModel> RuntimeOptionsProfileOptions =>
        CreateRuntimeOptionsOptions("profile", RuntimeOptionsProfileValues);

    public IReadOnlyList<NodeConfigOptionItemViewModel> RuntimeOptionsLogLevelOptions =>
        CreateRuntimeOptionsOptions("log_level", RuntimeOptionsLogLevelValues);

    public IReadOnlyList<NodeConfigOptionItemViewModel> RuntimeOptionsEventLevelOptions =>
        CreateRuntimeOptionsOptions("event_level", RuntimeOptionsEventLevelValues);

    public IReadOnlyList<NodeConfigOptionItemViewModel> RuntimeOptionsMaskPolicyOptions =>
        CreateRuntimeOptionsOptions("mask_policy", RuntimeOptionsMaskPolicyValues);

    public bool HasSelectedRuntimeOptionsNode => SelectedRuntimeOptionsNode is not null;

    public bool HasRuntimeOptionsEditorError =>
        !string.IsNullOrWhiteSpace(RuntimeOptionsEditorErrorMessage);

    public string RuntimeOptionsSummaryText =>
        F(
            "definition.runtime_options_summary",
            FormatRuntimeOptionsOptionValue("profile", RuntimeOptionsProfileDraft),
            FormatRuntimeOptionsOptionValue("event_level", RuntimeOptionsEventLevelDraft),
            RuntimeOptionsProgressEnabledDraft ? T("common.on") : T("common.off"),
            RuntimeOptionsNodeOverrideCount);

    public bool HasSelectedRunRuntimeOptionsSummary => SelectedRun is not null;

    public string SelectedRunRuntimeOptionsSummaryText =>
        FormatSelectedRunRuntimeOptionsSummary();

    public string RuntimeOptionsSectionText => T("definition.runtime_options");

    public string RuntimeOptionsOpenEditorText =>
        T("definition.runtime_options_open_editor");

    public string RuntimeOptionsWindowTitleText =>
        T("definition.runtime_options_window_title");

    public string RuntimeOptionsWorkflowSectionText =>
        T("definition.runtime_options_workflow_section");

    public string RuntimeOptionsNodeOverrideSectionText =>
        T("definition.runtime_options_node_override_section");

    public string RuntimeOptionsProfileText => T("definition.runtime_options_profile");

    public string RuntimeOptionsStrictValidationText =>
        T("definition.runtime_options_strict_validation");

    public string RuntimeOptionsLogLevelText => T("definition.runtime_options_log_level");

    public string RuntimeOptionsEventLevelText =>
        T("definition.runtime_options_event_level");

    public string RuntimeOptionsEventRateLimitText =>
        T("definition.runtime_options_event_rate_limit");

    public string RuntimeOptionsProgressEnabledText =>
        T("definition.runtime_options_progress_enabled");

    public string RuntimeOptionsProgressIntervalText =>
        T("definition.runtime_options_progress_interval");

    public string RuntimeOptionsCaptureErrorContextText =>
        T("definition.runtime_options_capture_error_context");

    public string RuntimeOptionsIncludeMetricsText =>
        T("definition.runtime_options_include_metrics");

    public string RuntimeOptionsPayloadByteLimitText =>
        T("definition.runtime_options_payload_byte_limit");

    public string RuntimeOptionsTtlSecondsText =>
        T("definition.runtime_options_ttl_seconds");

    public string RuntimeOptionsRedactColumnsText =>
        T("definition.runtime_options_redact_columns");

    public string RuntimeOptionsMaskPolicyText =>
        T("definition.runtime_options_mask_policy");

    public string RuntimeOptionsSelectNodeText =>
        T("definition.runtime_options_select_node");

    public string RuntimeOptionsApplyText => T("definition.runtime_options_apply");

    public string RuntimeOptionsResetNodeOverrideText =>
        T("definition.runtime_options_reset_node_override");

    private bool CanApplyRuntimeOptionsDraft()
    {
        return HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict;
    }

    private bool CanResetRuntimeOptionsSelectedNodeOverride()
    {
        return CanApplyRuntimeOptionsDraft()
            && SelectedRuntimeOptionsNode is not null;
    }

    [RelayCommand(CanExecute = nameof(CanApplyRuntimeOptionsDraft))]
    private void ApplyRuntimeOptionsDraft()
    {
        if (IsRuntimeOptionsJsonEditorExpanded && IsRuntimeOptionsJsonDraftDirty)
        {
            ApplyRuntimeOptionsJsonDraft();
            return;
        }

        ApplyRuntimeOptionsStructuredDraft();
    }

    private void ApplyRuntimeOptionsStructuredDraft()
    {
        var readResult = ReadWorkflowDefinitionDraftRuntimeOptionsFromCache();
        if (!readResult.Succeeded)
        {
            RuntimeOptionsEditorErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(readResult.Warning);
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        if (!TryBuildRuntimeOptionsDraftFromStructuredInputs(
            readResult.Draft,
            out var draft,
            out var errorMessage))
        {
            RuntimeOptionsEditorErrorMessage = errorMessage;
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        ApplyRuntimeOptionsDraftToWorkflow(draft);
    }

    [RelayCommand(CanExecute = nameof(CanResetRuntimeOptionsSelectedNodeOverride))]
    private void ResetRuntimeOptionsSelectedNodeOverride()
    {
        if (SelectedRuntimeOptionsNode is null)
        {
            return;
        }

        var readResult = ReadWorkflowDefinitionDraftRuntimeOptionsFromCache();
        if (!readResult.Succeeded)
        {
            RuntimeOptionsEditorErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(readResult.Warning);
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        var nodeOverrides =
            new Dictionary<string, RuntimeOptionsNodeOverrideDraft>(
                readResult.Draft.NodeOverrides);
        nodeOverrides.Remove(SelectedRuntimeOptionsNode.NodeInstanceId);
        var draft = readResult.Draft with
        {
            NodeOverrides = nodeOverrides,
        };
        var patchResult = WorkflowDefinitionDraftRuntimeOptionsPatcher.Apply(
            WorkflowDefinitionDraftJson,
            draft);
        if (!patchResult.Succeeded)
        {
            RuntimeOptionsEditorErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        RefreshSelectedRuntimeOptionsNodeDraftState(draft);
        RuntimeOptionsEditorErrorMessage = null;
        OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
        WorkflowDefinitionValidationMessage =
            T("definition.runtime_options_node_override_reset");
        WorkflowDefinitionValidationErrorMessage = null;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.runtime_options",
            UiNotificationKind.Success);
    }

    private void RefreshRuntimeOptionsDraftState()
    {
        var readResult = ReadWorkflowDefinitionDraftRuntimeOptionsFromCache();
        var draft = readResult.Succeeded ? readResult.Draft : new RuntimeOptionsDraft();
        var workflowFieldState =
            RuntimeOptionsDraftStateMapper.ToWorkflowFieldState(draft.Workflow);

        RuntimeOptionsProfileDraft = workflowFieldState.Profile;
        RuntimeOptionsStrictValidationDraft = workflowFieldState.StrictValidation;
        RuntimeOptionsLogLevelDraft = workflowFieldState.LogLevel;
        RuntimeOptionsEventLevelDraft = workflowFieldState.EventLevel;
        RuntimeOptionsEventRateLimitPerSecondDraft =
            workflowFieldState.EventRateLimitPerSecond;
        RuntimeOptionsProgressEnabledDraft = workflowFieldState.ProgressEnabled;
        RuntimeOptionsProgressIntervalSecondsDraft =
            workflowFieldState.ProgressIntervalSeconds;
        RuntimeOptionsCaptureErrorContextDraft =
            workflowFieldState.CaptureErrorContext;
        RuntimeOptionsIncludeMetricsDraft = workflowFieldState.IncludeMetrics;
        RuntimeOptionsPayloadByteLimitDraft =
            workflowFieldState.PayloadByteLimit;
        RuntimeOptionsTtlSecondsDraft = workflowFieldState.TtlSeconds;
        RuntimeOptionsRedactColumnsDraft = workflowFieldState.RedactColumns;
        RuntimeOptionsMaskPolicyDraft = workflowFieldState.MaskPolicy;
        RuntimeOptionsNodeOverrideCount = draft.NodeOverrides.Count;
        RuntimeOptionsEditorErrorMessage =
            readResult.Succeeded
                ? null
                : LocalizeWorkflowDefinitionDraftWarning(readResult.Warning);

        if (SelectedRuntimeOptionsNode is not null &&
            !WorkflowDefinitionDraftNodes.Contains(SelectedRuntimeOptionsNode))
        {
            SelectedRuntimeOptionsNode = null;
        }

        RefreshSelectedRuntimeOptionsNodeDraftState(draft);
        NotifyRuntimeOptionsSummaryChanged();
        OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
    }

    private void RefreshSelectedRuntimeOptionsNodeDraftState(
        RuntimeOptionsDraft? currentDraft = null)
    {
        var draft = currentDraft;
        if (draft is null)
        {
            var readResult = ReadWorkflowDefinitionDraftRuntimeOptionsFromCache();
            draft = readResult.Succeeded ? readResult.Draft : new RuntimeOptionsDraft();
        }

        var selectedNodeFieldState =
            RuntimeOptionsDraftStateMapper.ToSelectedNodeFieldState(
                draft,
                SelectedRuntimeOptionsNode?.NodeInstanceId);
        RuntimeOptionsSelectedNodeProfileDraft =
            selectedNodeFieldState.Profile ?? RuntimeOptionsDefaults.Profile;
        RuntimeOptionsSelectedNodeStrictValidationDraft =
            selectedNodeFieldState.StrictValidation ?? true;
        RuntimeOptionsSelectedNodeLogLevelDraft =
            selectedNodeFieldState.LogLevel ?? RuntimeOptionsDefaults.LogLevel;
        RuntimeOptionsSelectedNodeEventLevelDraft =
            selectedNodeFieldState.EventLevel ?? RuntimeOptionsDefaults.EventLevel;
        RuntimeOptionsSelectedNodeEventRateLimitPerSecondDraft =
            selectedNodeFieldState.EventRateLimitPerSecond ?? "0";
        RuntimeOptionsSelectedNodeProgressEnabledDraft =
            selectedNodeFieldState.ProgressEnabled ?? true;
        RuntimeOptionsSelectedNodeProgressIntervalSecondsDraft =
            selectedNodeFieldState.ProgressIntervalSeconds ?? "0";
        RuntimeOptionsSelectedNodeCaptureErrorContextDraft =
            selectedNodeFieldState.CaptureErrorContext ?? true;
        RuntimeOptionsSelectedNodeIncludeMetricsDraft =
            selectedNodeFieldState.IncludeMetrics ?? true;
        RuntimeOptionsSelectedNodePayloadByteLimitDraft =
            selectedNodeFieldState.PayloadByteLimit ?? "0";
        RuntimeOptionsSelectedNodeTtlSecondsDraft =
            selectedNodeFieldState.TtlSeconds ?? "0";
        RuntimeOptionsSelectedNodeRedactColumnsDraft =
            selectedNodeFieldState.RedactColumns ?? string.Empty;
        RuntimeOptionsSelectedNodeMaskPolicyDraft =
            selectedNodeFieldState.MaskPolicy ?? RuntimeOptionsDefaults.MaskPolicy;

        OnPropertyChanged(nameof(HasSelectedRuntimeOptionsNode));
        ResetRuntimeOptionsSelectedNodeOverrideCommand.NotifyCanExecuteChanged();
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    private bool TryBuildRuntimeOptionsDraftFromStructuredInputs(
        out RuntimeOptionsDraft draft,
        out string errorMessage)
    {
        var readResult = ReadWorkflowDefinitionDraftRuntimeOptionsFromCache();
        if (!readResult.Succeeded)
        {
            draft = new RuntimeOptionsDraft();
            errorMessage =
                LocalizeWorkflowDefinitionDraftWarning(readResult.Warning)
                ?? string.Empty;
            return false;
        }

        return TryBuildRuntimeOptionsDraftFromStructuredInputs(
            readResult.Draft,
            out draft,
            out errorMessage);
    }

    private bool TryBuildRuntimeOptionsDraftFromStructuredInputs(
        RuntimeOptionsDraft baseDraft,
        out RuntimeOptionsDraft draft,
        out string errorMessage)
    {
        draft = new RuntimeOptionsDraft();
        if (!TryBuildRuntimeOptionsWorkflowDraft(
            out var workflowDraft,
            out errorMessage))
        {
            return false;
        }

        var nodeOverrides =
            new Dictionary<string, RuntimeOptionsNodeOverrideDraft>(
                baseDraft.NodeOverrides);
        if (SelectedRuntimeOptionsNode is not null)
        {
            if (!TryBuildSelectedRuntimeOptionsNodeOverrideDraft(
                out var nodeOverride,
                out errorMessage))
            {
                return false;
            }

            nodeOverrides[SelectedRuntimeOptionsNode.NodeInstanceId] = nodeOverride;
        }

        draft = new RuntimeOptionsDraft
        {
            Version = RuntimeOptionsDefaults.Version,
            Workflow = workflowDraft,
            NodeOverrides = nodeOverrides,
        };
        return TryValidateRuntimeOptionsDraft(draft, out errorMessage);
    }

    private bool ApplyRuntimeOptionsDraftToWorkflow(RuntimeOptionsDraft draft)
    {
        var patchResult = WorkflowDefinitionDraftRuntimeOptionsPatcher.Apply(
            WorkflowDefinitionDraftJson,
            draft);
        if (!patchResult.Succeeded)
        {
            RuntimeOptionsEditorErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return false;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        RuntimeOptionsEditorErrorMessage = null;
        OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
        WorkflowDefinitionValidationMessage = T("definition.runtime_options_applied");
        WorkflowDefinitionValidationErrorMessage = null;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.runtime_options",
            UiNotificationKind.Success);
        if (IsRuntimeOptionsJsonEditorExpanded && !IsRuntimeOptionsJsonDraftDirty)
        {
            SetRuntimeOptionsJsonDraft(
                WorkflowDefinitionDraftRuntimeOptionsPatcher.FormatRuntimeOptions(draft),
                isDirty: false);
        }

        return true;
    }

    private bool TryBuildRuntimeOptionsWorkflowDraft(
        out RuntimeOptionsWorkflowDraft draft,
        out string errorMessage)
    {
        draft = new RuntimeOptionsWorkflowDraft();
        errorMessage = string.Empty;
        if (!TryParseNonNegativeInt(
            RuntimeOptionsEventRateLimitPerSecondDraft,
            RuntimeOptionsEventRateLimitText,
            out var eventRateLimit,
            out errorMessage) ||
            !TryParseNonNegativeDouble(
                RuntimeOptionsProgressIntervalSecondsDraft,
                RuntimeOptionsProgressIntervalText,
                out var progressInterval,
                out errorMessage) ||
            !TryParseNonNegativeInt(
                RuntimeOptionsPayloadByteLimitDraft,
                RuntimeOptionsPayloadByteLimitText,
                out var payloadByteLimit,
                out errorMessage) ||
            !TryParseNonNegativeInt(
                RuntimeOptionsTtlSecondsDraft,
                RuntimeOptionsTtlSecondsText,
                out var ttlSeconds,
                out errorMessage))
        {
            return false;
        }

        draft = new RuntimeOptionsWorkflowDraft
        {
            Profile = RuntimeOptionsProfileDraft,
            StrictValidation = RuntimeOptionsStrictValidationDraft,
            Telemetry = new RuntimeOptionsTelemetryDraft
            {
                LogLevel = RuntimeOptionsLogLevelDraft,
                EventLevel = RuntimeOptionsEventLevelDraft,
                EventRateLimitPerSecond = eventRateLimit,
                ProgressEnabled = RuntimeOptionsProgressEnabledDraft,
                ProgressIntervalSeconds = progressInterval,
            },
            Diagnostics = new RuntimeOptionsDiagnosticsDraft
            {
                CaptureErrorContext = RuntimeOptionsCaptureErrorContextDraft,
                IncludeMetrics = RuntimeOptionsIncludeMetricsDraft,
                PayloadByteLimit = payloadByteLimit,
                TtlSeconds = ttlSeconds,
                RedactColumns = RuntimeOptionsDraftStateMapper.ParseRedactColumns(
                    RuntimeOptionsRedactColumnsDraft),
                MaskPolicy = RuntimeOptionsMaskPolicyDraft,
            },
        };
        return true;
    }

    private bool TryBuildSelectedRuntimeOptionsNodeOverrideDraft(
        out RuntimeOptionsNodeOverrideDraft draft,
        out string errorMessage)
    {
        draft = new RuntimeOptionsNodeOverrideDraft();
        errorMessage = string.Empty;
        if (!TryParseNonNegativeInt(
            RuntimeOptionsSelectedNodeEventRateLimitPerSecondDraft,
            RuntimeOptionsEventRateLimitText,
            out var eventRateLimit,
            out errorMessage) ||
            !TryParseNonNegativeDouble(
                RuntimeOptionsSelectedNodeProgressIntervalSecondsDraft,
                RuntimeOptionsProgressIntervalText,
                out var progressInterval,
                out errorMessage) ||
            !TryParseNonNegativeInt(
                RuntimeOptionsSelectedNodePayloadByteLimitDraft,
                RuntimeOptionsPayloadByteLimitText,
                out var payloadByteLimit,
                out errorMessage) ||
            !TryParseNonNegativeInt(
                RuntimeOptionsSelectedNodeTtlSecondsDraft,
                RuntimeOptionsTtlSecondsText,
                out var ttlSeconds,
                out errorMessage))
        {
            return false;
        }

        draft = new RuntimeOptionsNodeOverrideDraft
        {
            Profile = RuntimeOptionsSelectedNodeProfileDraft,
            StrictValidation = RuntimeOptionsSelectedNodeStrictValidationDraft,
            Telemetry = new RuntimeOptionsTelemetryOverrideDraft
            {
                LogLevel = RuntimeOptionsSelectedNodeLogLevelDraft,
                EventLevel = RuntimeOptionsSelectedNodeEventLevelDraft,
                EventRateLimitPerSecond = eventRateLimit,
                ProgressEnabled = RuntimeOptionsSelectedNodeProgressEnabledDraft,
                ProgressIntervalSeconds = progressInterval,
            },
            Diagnostics = new RuntimeOptionsDiagnosticsOverrideDraft
            {
                CaptureErrorContext =
                    RuntimeOptionsSelectedNodeCaptureErrorContextDraft,
                IncludeMetrics = RuntimeOptionsSelectedNodeIncludeMetricsDraft,
                PayloadByteLimit = payloadByteLimit,
                TtlSeconds = ttlSeconds,
                RedactColumns = RuntimeOptionsDraftStateMapper.ParseRedactColumns(
                    RuntimeOptionsSelectedNodeRedactColumnsDraft),
                MaskPolicy = RuntimeOptionsSelectedNodeMaskPolicyDraft,
            },
        };
        return true;
    }

    private void NotifyRuntimeOptionsSummaryChanged()
    {
        OnPropertyChanged(nameof(RuntimeOptionsSummaryText));
    }

    private IReadOnlyList<NodeConfigOptionItemViewModel> CreateRuntimeOptionsOptions(
        string group,
        IReadOnlyList<string> values)
    {
        return values
            .Select(value => new NodeConfigOptionItemViewModel(
                value,
                FormatRuntimeOptionsOptionValue(group, value)))
            .ToArray();
    }

    private string FormatRuntimeOptionsOptionValue(string group, string value)
    {
        return DisplayTextFormatter.FormatRuntimeOptionsOptionValue(group, value);
    }

    private string FormatSelectedRunRuntimeOptionsSummary()
    {
        if (SelectedRun is null)
        {
            return T("definition.runtime_options_run_summary_empty");
        }

        var definitionJson = FindSelectedRunDefinitionJson();
        if (definitionJson is null)
        {
            return T("definition.runtime_options_run_summary_unavailable");
        }

        var readResult = RuntimeOptionsDraftReader.Read(definitionJson);
        if (!readResult.Succeeded)
        {
            return LocalizeWorkflowDefinitionDraftWarning(readResult.Warning)
                ?? readResult.Warning
                ?? T("definition.runtime_options_run_summary_unavailable");
        }

        return F(
            "definition.runtime_options_run_summary",
            FormatRuntimeOptionsOptionValue("profile", readResult.Draft.Workflow.Profile),
            FormatRuntimeOptionsOptionValue(
                "event_level",
                readResult.Draft.Workflow.Telemetry.EventLevel),
            readResult.Draft.Workflow.Telemetry.ProgressEnabled
                ? T("common.on")
                : T("common.off"),
            readResult.Draft.NodeOverrides.Count);
    }

    private string? FindSelectedRunDefinitionJson()
    {
        if (SelectedRun is null ||
            WorkflowDefinitionDetail is null ||
            !string.Equals(
                SelectedRun.WorkflowId,
                WorkflowDefinitionDetail.WorkflowId,
                StringComparison.Ordinal))
        {
            return null;
        }

        if (string.Equals(
            SelectedRun.RevisionId,
            WorkflowDefinitionDetail.RevisionId,
            StringComparison.Ordinal) ||
            (string.IsNullOrWhiteSpace(SelectedRun.RevisionId) &&
                SelectedRun.WorkflowVersion == WorkflowDefinitionDetail.Version))
        {
            return WorkflowDefinitionDetail.RawDefinitionJson;
        }

        return WorkflowDefinitionDetail.Revisions.FirstOrDefault(revision =>
            string.Equals(
                revision.RevisionId,
                SelectedRun.RevisionId,
                StringComparison.Ordinal))?.RawDefinitionJson;
    }

    partial void OnSelectedRuntimeOptionsNodeChanged(
        WorkflowDefinitionNodeListItemViewModel? value)
    {
        OnPropertyChanged(nameof(HasSelectedRuntimeOptionsNode));
        RefreshSelectedRuntimeOptionsNodeDraftState();
        ResetRuntimeOptionsSelectedNodeOverrideCommand.NotifyCanExecuteChanged();
    }

    partial void OnRuntimeOptionsProfileDraftChanged(string value)
    {
        NotifyRuntimeOptionsSummaryChanged();
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsStrictValidationDraftChanged(bool value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsLogLevelDraftChanged(string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsEventLevelDraftChanged(string value)
    {
        NotifyRuntimeOptionsSummaryChanged();
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsEventRateLimitPerSecondDraftChanged(string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsProgressEnabledDraftChanged(bool value)
    {
        NotifyRuntimeOptionsSummaryChanged();
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsProgressIntervalSecondsDraftChanged(string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsCaptureErrorContextDraftChanged(bool value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsIncludeMetricsDraftChanged(bool value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsPayloadByteLimitDraftChanged(string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsTtlSecondsDraftChanged(string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsRedactColumnsDraftChanged(string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsMaskPolicyDraftChanged(string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeProfileDraftChanged(string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeStrictValidationDraftChanged(bool value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeLogLevelDraftChanged(string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeEventLevelDraftChanged(string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeEventRateLimitPerSecondDraftChanged(
        string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeProgressEnabledDraftChanged(bool value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeProgressIntervalSecondsDraftChanged(
        string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeCaptureErrorContextDraftChanged(bool value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeIncludeMetricsDraftChanged(bool value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodePayloadByteLimitDraftChanged(string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeTtlSecondsDraftChanged(string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeRedactColumnsDraftChanged(string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeMaskPolicyDraftChanged(string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsNodeOverrideCountChanged(int value)
    {
        NotifyRuntimeOptionsSummaryChanged();
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsEditorErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
    }

}
