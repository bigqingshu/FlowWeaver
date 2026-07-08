using System.Collections.ObjectModel;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Localization;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

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

    [RelayCommand]
    private async Task ChangeLanguageAsync(string? languageCode)
    {
        await ApplyLanguageAsync(
            languageCode ?? SupportedLanguage.Default.Code,
            save: true,
            _shutdown.Token);
    }

    [RelayCommand]
    private async Task ChangeThemeAsync(string? themeVariantStr)
    {
        await ApplyThemeAsync(
            themeVariantStr ?? PersistedUiSettings.SystemThemeVariant,
            save: true,
            _shutdown.Token);
    }

    private async Task ApplyLanguageAsync(
        string languageCode,
        bool save,
        CancellationToken cancellationToken)
    {
        var previousDefaults = CaptureDefaultMessageSnapshot();
        await _localizationService.SetLanguageAsync(languageCode, cancellationToken);
        CurrentLanguageCode = _localizationService.CurrentLanguageCode;
        foreach (var language in Languages)
        {
            language.IsSelected = language.Code == CurrentLanguageCode;
        }

        NotifyLocalizedTextChanged();
        RefreshDefaultMessagesForCurrentLanguage(previousDefaults);
        if (save)
        {
            await _uiSettingsStore.SaveAsync(
                PersistedUiSettings.FromSettings(CurrentLanguageCode, CurrentThemeVariant),
                cancellationToken);
        }
    }

    private async Task ApplyThemeAsync(
        string themeVariant,
        bool save,
        CancellationToken cancellationToken)
    {
        CurrentThemeVariant = PersistedUiSettings.NormalizeThemeVariantOrDefault(themeVariant);
        foreach (var theme in Themes)
        {
            theme.IsSelected = theme.ThemeVariant == CurrentThemeVariant;
        }

        if (Avalonia.Application.Current != null)
        {
            Avalonia.Application.Current.RequestedThemeVariant = CurrentThemeVariant switch
            {
                PersistedUiSettings.LightThemeVariant => Avalonia.Styling.ThemeVariant.Light,
                PersistedUiSettings.DarkThemeVariant => Avalonia.Styling.ThemeVariant.Dark,
                _ => Avalonia.Styling.ThemeVariant.Default
            };
        }

        OnPropertyChanged(nameof(ThemeMenuHeaderText));

        if (save)
        {
            await _uiSettingsStore.SaveAsync(
                PersistedUiSettings.FromSettings(CurrentLanguageCode, CurrentThemeVariant),
                cancellationToken);
        }
    }

    private string T(string key)
    {
        return _localizationService.GetString(key);
    }

    private string F(string key, params object?[] args)
    {
        return _localizationService.Format(key, args);
    }

}
