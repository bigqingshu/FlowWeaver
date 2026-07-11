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
    private readonly ISharedPublicationCatalogService _sharedPublicationCatalogService;
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
        IWorkflowExportFileService? workflowExportFileService = null,
        Func<CancellationToken, Task>? workflowDraftJsonDebounceDelay = null)
    {
        _healthClient = healthClient;
        _apiClient = apiClient;
        _runtimeEventStreamClient = runtimeEventStreamClient;
        _runtimeEventReconnectDelay = runtimeEventReconnectDelay
            ?? (cancellationToken => Task.Delay(TimeSpan.FromSeconds(2), cancellationToken));
        _dataPreviewRunRefreshDelay = dataPreviewRunRefreshDelay
            ?? (cancellationToken => Task.Delay(TimeSpan.FromMilliseconds(250), cancellationToken));
        _workflowDraftJsonDebounceDelay = workflowDraftJsonDebounceDelay
            ?? (cancellationToken => Task.Delay(TimeSpan.FromMilliseconds(250), cancellationToken));
        _connectionSettingsStore = connectionSettingsStore ?? new FileConnectionSettingsStore();
        _uiSettingsStore = uiSettingsStore ?? new FileUiSettingsStore();
        _workflowImportFileService =
            workflowImportFileService ?? new AvaloniaWorkflowImportFileService();
        _workflowExportFileService =
            workflowExportFileService ?? new AvaloniaWorkflowExportFileService();
        _localizationService = localizationService ?? new JsonLocalizationService();
        _sharedPublicationCatalogService = new SharedPublicationCatalogService(
            apiClient,
            BuildSettings);

        InitializeWorkflowLoopRegions();
        InitializeWorkflowNodeTableBindings();
        InitializeRunLoopMonitor(apiClient);
        InitializeBackgroundRunManagement(apiClient);
        InitializeLanguageMenuItems();
        InitializeThemeMenuItems();
        RefreshDefaultMessagesForCurrentLanguage(previousDefaults: null);
        RefreshShellNavigationItems();
        RefreshSelectedNodeConfigDraftState();
    }
}
