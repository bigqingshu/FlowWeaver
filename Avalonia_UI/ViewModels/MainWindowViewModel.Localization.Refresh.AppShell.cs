namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyAppShellAndConnectionLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(AppTitleText));
        OnPropertyChanged(nameof(AppSubtitleText));
        OnPropertyChanged(nameof(SettingsMenuText));
        OnPropertyChanged(nameof(LanguageMenuText));
        OnPropertyChanged(nameof(LanguageMenuHeaderText));
        OnPropertyChanged(nameof(ThemeMenuText));
        OnPropertyChanged(nameof(ThemeMenuHeaderText));
        OnPropertyChanged(nameof(LightThemeText));
        OnPropertyChanged(nameof(DarkThemeText));
        OnPropertyChanged(nameof(SystemThemeText));
        OnPropertyChanged(nameof(EnglishLanguageText));
        OnPropertyChanged(nameof(SimplifiedChineseLanguageText));
        OnPropertyChanged(nameof(ConnectionBaseUrlText));
        OnPropertyChanged(nameof(ConnectionTokenText));
        OnPropertyChanged(nameof(ConnectionStatusText));
        OnPropertyChanged(nameof(ConnectionEventsText));
        OnPropertyChanged(nameof(CheckConnectionText));
        OnPropertyChanged(nameof(StreamText));
        OnPropertyChanged(nameof(StopText));
        OnPropertyChanged(nameof(RefreshNodeDefinitionsDisabledReasonText));
        OnPropertyChanged(nameof(ExecutionTabText));
        OnPropertyChanged(nameof(DefinitionTabText));
        OnPropertyChanged(nameof(LogsTabText));
        OnPropertyChanged(nameof(DataTabText));
        OnPropertyChanged(nameof(DataPreviewTabText));
    }
}
