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

}
