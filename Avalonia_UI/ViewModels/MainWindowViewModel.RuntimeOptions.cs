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
