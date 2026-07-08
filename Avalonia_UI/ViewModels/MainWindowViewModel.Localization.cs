using System.Collections.ObjectModel;
using Avalonia_UI.Localization;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private string currentLanguageCode = SupportedLanguage.Default.Code;

    [ObservableProperty]
    private string currentThemeVariant = PersistedUiSettings.SystemThemeVariant;

    public ObservableCollection<LanguageMenuItemViewModel> Languages { get; } = new();

    public ObservableCollection<ThemeMenuItemViewModel> Themes { get; } = new();

    public string AppTitleText => T("app.title");

    public string AppSubtitleText => T("app.subtitle");

    public string SettingsMenuText => T("settings.menu");

    public string LanguageMenuText => T("settings.language");

    public string LanguageMenuHeaderText => $"{LanguageMenuText}: {T($"language.{CurrentLanguageCode}")}";

    public string ThemeMenuText => T("settings.theme");

    public string ThemeMenuHeaderText => $"{ThemeMenuText}: {T($"theme.{CurrentThemeVariant.ToLowerInvariant()}")}";

    public string LightThemeText => T("theme.light");

    public string DarkThemeText => T("theme.dark");

    public string SystemThemeText => T("theme.system");

    public string EnglishLanguageText => T("language.en-US");

    public string SimplifiedChineseLanguageText => T("language.zh-Hans");

    private string T(string key)
    {
        return _localizationService.GetString(key);
    }

    private string F(string key, params object?[] args)
    {
        return _localizationService.Format(key, args);
    }

}
