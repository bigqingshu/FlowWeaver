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
        Func<CancellationToken, Task>? dataPreviewRunRefreshDelay = null)
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

    private DisplayTextFormatter DisplayTextFormatter => new(_localizationService);

    public string ExecutionTabText => T("tab.execution");

    public string DefinitionTabText => T("tab.definition");

    public string LogsTabText => T("tab.logs");

    public string DataTabText => T("tab.data");

    public string DataPreviewTabText => T("tab.data_preview");

    public string WorkflowsSectionText => T("workflow.section");

    public string RefreshText => T("common.refresh");

    public string CloseText => T("common.close");

    public string RunText => T("workflow.run");

    public string CreateText => T("workflow.create");

    public string ImportWorkflowText => T("workflow.import");

    public string ExportWorkflowText => T("workflow.export");

    public string DeleteWorkflowText => T("workflow.delete");

    public string DeleteWorkflowConfirmTitleText => T("workflow.delete_confirm_title");

    public string DeleteWorkflowConfirmMessageText => T("workflow.delete_confirm_message");

    public string WorkflowNameWatermarkText => T("workflow.name_watermark");

    public string RunsSectionText => T("runs.section");

    public string CancelText => T("runs.cancel");

    public string CancelConfirmTitleText => T("runs.cancel_confirm_title");

    public string CancelConfirmMessageText => T("runs.cancel_confirm_message");

    public string NodeRunsSectionText => T("node_runs.section");

    public async Task LoadUiSettingsAsync(
        CancellationToken cancellationToken = default)
    {
        try
        {
            var settings = await _uiSettingsStore.LoadAsync(cancellationToken);
            await ApplyThemeAsync(settings.ThemeVariant, save: false, cancellationToken);
            await ApplyLanguageAsync(settings.LanguageCode, save: false, cancellationToken);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception ex)
        {
            ErrorMessage = F("format.ui_settings_load_failed", ex.Message);
        }
    }

    private void NotifyEngineActionStateChanged()
    {
        OnPropertyChanged(nameof(CanUseEngineActions));
        OnPropertyChanged(nameof(CanUseCancelSelectedRunAction));
        OnPropertyChanged(nameof(CancelSelectedRunDisabledReasonText));
        OnPropertyChanged(nameof(RefreshNodeDefinitionsDisabledReasonText));
        RefreshWorkflowsCommand.NotifyCanExecuteChanged();
        CreateTemplateWorkflowCommand.NotifyCanExecuteChanged();
        DeleteSelectedWorkflowCommand.NotifyCanExecuteChanged();
        OnPropertyChanged(nameof(CanUseDeleteSelectedWorkflowAction));
        OnPropertyChanged(nameof(DeleteSelectedWorkflowDisabledReasonText));
        StartSelectedWorkflowCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
        RefreshRunsCommand.NotifyCanExecuteChanged();
        CancelSelectedRunCommand.NotifyCanExecuteChanged();
        RefreshNodeRunsCommand.NotifyCanExecuteChanged();
        LoadSelectedWorkflowDefinitionCommand.NotifyCanExecuteChanged();
        RefreshNodeDefinitionsCommand.NotifyCanExecuteChanged();
        ValidateWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
        ApplyRuntimeOptionsDraftCommand.NotifyCanExecuteChanged();
        RegenerateRuntimeOptionsJsonDraftCommand.NotifyCanExecuteChanged();
        ResetRuntimeOptionsSelectedNodeOverrideCommand.NotifyCanExecuteChanged();
        AddWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
        NotifyWorkflowDefinitionNodeActionCommandsChanged();
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        DeleteWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        SaveWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        RefreshRuntimeEventLogCommand.NotifyCanExecuteChanged();
        RefreshTableRefsCommand.NotifyCanExecuteChanged();
        RefreshSelectedWorkflowNodeDataPreviewCommand.NotifyCanExecuteChanged();
        ShowDataPreviewDetailsCommand.NotifyCanExecuteChanged();
        LoadSelectedDataPreviewTableCommand.NotifyCanExecuteChanged();
        RefreshSharedPublicationsCommand.NotifyCanExecuteChanged();
        RefreshSharedPublicationVersionsCommand.NotifyCanExecuteChanged();
    }

}
