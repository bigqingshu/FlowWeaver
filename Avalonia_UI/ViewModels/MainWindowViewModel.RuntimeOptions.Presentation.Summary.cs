namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public string RuntimeOptionsSummaryText =>
        F(
            "definition.runtime_options_summary",
            FormatRuntimeOptionsOptionValue("profile", RuntimeOptionsProfileDraft),
            FormatRuntimeOptionsOptionValue("event_level", RuntimeOptionsEventLevelDraft),
            RuntimeOptionsProgressEnabledDraft ? T("common.on") : T("common.off"),
            RuntimeOptionsNodeOverrideCount);

    private void NotifyRuntimeOptionsSummaryChanged()
    {
        OnPropertyChanged(nameof(RuntimeOptionsSummaryText));
    }
}
