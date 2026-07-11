namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyRuntimeOptionsLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(RuntimeOptionsSectionText));
        OnPropertyChanged(nameof(RuntimeOptionsOpenEditorText));
        OnPropertyChanged(nameof(RuntimeOptionsWindowTitleText));
        OnPropertyChanged(nameof(RuntimeOptionsWorkflowSectionText));
        OnPropertyChanged(nameof(RuntimeOptionsNodeOverrideSectionText));
        OnPropertyChanged(nameof(RuntimeOptionsProfileText));
        OnPropertyChanged(nameof(RuntimeOptionsProfileOptions));
        OnPropertyChanged(nameof(RuntimeOptionsStrictValidationText));
        OnPropertyChanged(nameof(RuntimeOptionsLogLevelText));
        OnPropertyChanged(nameof(RuntimeOptionsLogLevelOptions));
        OnPropertyChanged(nameof(RuntimeOptionsEventLevelText));
        OnPropertyChanged(nameof(RuntimeOptionsEventLevelOptions));
        OnPropertyChanged(nameof(RuntimeOptionsEventRateLimitText));
        OnPropertyChanged(nameof(RuntimeOptionsProgressEnabledText));
        OnPropertyChanged(nameof(RuntimeOptionsProgressIntervalText));
        OnPropertyChanged(nameof(RuntimeOptionsCaptureErrorContextText));
        OnPropertyChanged(nameof(RuntimeOptionsIncludeMetricsText));
        OnPropertyChanged(nameof(RuntimeOptionsPayloadByteLimitText));
        OnPropertyChanged(nameof(RuntimeOptionsTtlSecondsText));
        OnPropertyChanged(nameof(RuntimeOptionsRedactColumnsText));
        OnPropertyChanged(nameof(RuntimeOptionsMaskPolicyText));
        OnPropertyChanged(nameof(RuntimeOptionsMaskPolicyOptions));
        OnPropertyChanged(nameof(RuntimeOptionsJsonSectionText));
        OnPropertyChanged(nameof(RuntimeOptionsJsonRegenerateText));
        OnPropertyChanged(nameof(RuntimeOptionsJsonWatermarkText));
        OnPropertyChanged(nameof(RuntimeOptionsSelectNodeText));
        OnPropertyChanged(nameof(RuntimeOptionsApplyText));
        OnPropertyChanged(nameof(RuntimeOptionsResetNodeOverrideText));
        OnPropertyChanged(nameof(CurrentRunRuntimeOptionsOpenText));
        NotifyRuntimeOptionsSummaryChanged();
        OnPropertyChanged(nameof(SelectedRunRuntimeOptionsSummaryText));
    }
}
