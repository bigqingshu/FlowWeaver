using System;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;
using Avalonia_UI.Models;
using Avalonia_UI.Services;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel : ViewModelBase
{
    private readonly IEngineHostApiClient _apiClient;
    private readonly IUiSettingsStore _uiSettingsStore;
    private readonly IWorkflowImportFileService _workflowImportFileService;
    private readonly IWorkflowExportFileService _workflowExportFileService;
    private readonly ILocalizationService _localizationService;
    private readonly NodeEditorResolver _nodeEditorResolver = new(BuiltinNodeEditors.CreateRegistry());

    private readonly CancellationTokenSource _shutdown = new();

    public MainWindowViewModel()
        : this(new EngineHostApiClient())
    {
    }

    public MainWindowViewModel(IEngineHostApiClient apiClient)
        : this(new EngineHostHealthClient(apiClient), apiClient)
    {
    }

    public MainWindowViewModel(EngineHostHealthClient healthClient)
        : this(healthClient, new EngineHostApiClient())
    {
    }

    public MainWindowViewModel(
        EngineHostHealthClient healthClient,
        IEngineHostApiClient apiClient)
        : this(
            healthClient,
            apiClient,
            new EngineHostRuntimeEventStreamClient())
    {
    }

    public MainWindowViewModel(
        EngineHostHealthClient healthClient,
        IEngineHostApiClient apiClient,
        IEngineHostRuntimeEventStreamClient runtimeEventStreamClient,
        Func<CancellationToken, Task>? runtimeEventReconnectDelay = null,
        IConnectionSettingsStore? connectionSettingsStore = null,
        IUiSettingsStore? uiSettingsStore = null,
        ILocalizationService? localizationService = null,
        Func<CancellationToken, Task>? dataPreviewRunRefreshDelay = null,
        IWorkflowImportFileService? workflowImportFileService = null,
        IWorkflowExportFileService? workflowExportFileService = null)
    {
        _healthClient = healthClient;
        _apiClient = apiClient;
        _runtimeEventStreamClient = runtimeEventStreamClient;
        _runtimeEventReconnectDelay = runtimeEventReconnectDelay
            ?? (cancellationToken => Task.Delay(TimeSpan.FromSeconds(2), cancellationToken));
        _dataPreviewRunRefreshDelay = dataPreviewRunRefreshDelay
            ?? (cancellationToken => Task.Delay(TimeSpan.FromMilliseconds(250), cancellationToken));
        _connectionSettingsStore = connectionSettingsStore ?? new FileConnectionSettingsStore();
        _uiSettingsStore = uiSettingsStore ?? new FileUiSettingsStore();
        _workflowImportFileService =
            workflowImportFileService ?? new AvaloniaWorkflowImportFileService();
        _workflowExportFileService =
            workflowExportFileService ?? new AvaloniaWorkflowExportFileService();
        _localizationService = localizationService ?? new JsonLocalizationService();
        CurrentLanguageCode = _localizationService.CurrentLanguageCode;
        foreach (var language in _localizationService.SupportedLanguages)
        {
            Languages.Add(
                new LanguageMenuItemViewModel(language)
                {
                    IsSelected = language.Code == CurrentLanguageCode,
                });
        }

        Themes.Add(new ThemeMenuItemViewModel("Light", PersistedUiSettings.LightThemeVariant));
        Themes.Add(new ThemeMenuItemViewModel("Dark", PersistedUiSettings.DarkThemeVariant));
        Themes.Add(new ThemeMenuItemViewModel("System", PersistedUiSettings.SystemThemeVariant));

        foreach (var theme in Themes)
        {
            theme.IsSelected = theme.ThemeVariant == CurrentThemeVariant;
        }

        RefreshDefaultMessagesForCurrentLanguage(previousDefaults: null);
        RefreshShellNavigationItems();
        RefreshSelectedNodeConfigDraftState();
    }
}
