using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

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
