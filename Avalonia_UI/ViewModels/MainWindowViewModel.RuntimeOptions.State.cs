using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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

}
