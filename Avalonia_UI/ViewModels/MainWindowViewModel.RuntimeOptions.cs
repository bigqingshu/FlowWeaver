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
