using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;
using Avalonia_UI.Models;
using Avalonia_UI.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel : ViewModelBase
{
    private const int MaxRuntimeEvents = 50;
    private const int DataPreviewRowLimit = 50;
    private const int DataPreviewRunRefreshAttemptCount = 8;
    private const int WorkflowRunTerminalRefreshAttemptCount = 40;

    private readonly IEngineHostApiClient _apiClient;
    private readonly EngineHostHealthClient _healthClient;
    private readonly IEngineHostRuntimeEventStreamClient _runtimeEventStreamClient;
    private readonly Func<CancellationToken, Task> _runtimeEventReconnectDelay;
    private readonly Func<CancellationToken, Task> _dataPreviewRunRefreshDelay;
    private readonly IConnectionSettingsStore _connectionSettingsStore;
    private readonly IUiSettingsStore _uiSettingsStore;
    private readonly ILocalizationService _localizationService;
    private readonly NodeEditorResolver _nodeEditorResolver = new(BuiltinNodeEditors.CreateRegistry());

    private readonly CancellationTokenSource _shutdown = new();
    private CancellationTokenSource? _runtimeEventStreamCancellation;
    private Task? _runtimeEventStreamTask;
    private int nodeRunsLoadVersion;
    private int nodeDefinitionsLoadVersion;
    private int tableRefsLoadVersion;
    private int sharedPublicationsLoadVersion;
    private int sharedPublicationVersionsLoadVersion;
    private int dataPreviewLoadVersion;
    private int runtimeEventLogLoadVersion;
    private int auditEventLogLoadVersion;
    private bool isSynchronizingShellSelection;
    private bool runtimeEventStreamAutoConnect;

    [ObservableProperty]
    private string baseUrl = EngineHostConnectionSettings.DefaultBaseUrl;

    [ObservableProperty]
    private string token = string.Empty;

    [ObservableProperty]
    private ConnectionStatus connectionStatus = ConnectionStatus.Disconnected;

    [ObservableProperty]
    private bool isAuthenticationFailed;

    [ObservableProperty]
    private string statusMessage = "Disconnected.";

    [ObservableProperty]
    private string? errorMessage;

    [ObservableProperty]
    private bool isLoadingWorkflows;

    [ObservableProperty]
    private bool isStartingWorkflow;

    [ObservableProperty]
    private string newWorkflowName = "Generated table workflow";

    [ObservableProperty]
    private bool isCreatingWorkflow;

    [ObservableProperty]
    private WorkflowListItemViewModel? selectedWorkflow;

    [ObservableProperty]
    private string workflowMessage = "No workflows loaded.";

    [ObservableProperty]
    private string? workflowErrorMessage;

    [ObservableProperty]
    private string? lastStartedRunId;

    [ObservableProperty]
    private string? lastStartedRunStatus;

    [ObservableProperty]
    private bool isLoadingWorkflowDefinition;

    [ObservableProperty]
    private WorkflowDefinitionDetailViewModel? workflowDefinitionDetail;

    [ObservableProperty]
    private WorkflowDefinitionNodeListItemViewModel? selectedWorkflowDefinitionNode;

    [ObservableProperty]
    private string selectedNodeDisplayNameDraft = string.Empty;

    [ObservableProperty]
    private NodeConfigDraft? selectedNodeConfigDraft;

    [ObservableProperty]
    private NodeConfigEditableDraft? selectedNodeConfigEditableDraft;

    [ObservableProperty]
    private string selectedNodeConfigEditableDraftMessage = string.Empty;

    [ObservableProperty]
    private string workflowDefinitionMessage = "Select a workflow to load definition.";

    [ObservableProperty]
    private string? workflowDefinitionErrorMessage;

    [ObservableProperty]
    private bool isLoadingNodeDefinitions;

    [ObservableProperty]
    private string nodeDefinitionCatalogMessage = "No node definitions loaded.";

    [ObservableProperty]
    private string? nodeDefinitionCatalogErrorMessage;

    [ObservableProperty]
    private string workflowDefinitionDraftJson = string.Empty;

    [ObservableProperty]
    private WorkflowDefinitionDraftStructure? workflowDefinitionDraftStructure;

    [ObservableProperty]
    private NodeDefinitionListItemViewModel? selectedNewDraftNodeDefinition;

    [ObservableProperty]
    private string newDraftNodeInstanceId = string.Empty;

    [ObservableProperty]
    private string newDraftNodeType = string.Empty;

    [ObservableProperty]
    private string newDraftNodeVersion = "1.0";

    [ObservableProperty]
    private string newDraftNodeDisplayName = string.Empty;

    [ObservableProperty]
    private string newDraftNodeConfigJson = "{}";

    [ObservableProperty]
    private string selectedWorkflowDefinitionDraftNodeInstanceId = string.Empty;

    [ObservableProperty]
    private WorkflowDefinitionDraftNode? selectedNewDraftConnectionSourceNode;

    [ObservableProperty]
    private WorkflowDefinitionDraftNode? selectedNewDraftConnectionTargetNode;

    [ObservableProperty]
    private string newDraftConnectionId = string.Empty;

    [ObservableProperty]
    private string newDraftConnectionSourceNodeId = string.Empty;

    [ObservableProperty]
    private string newDraftConnectionSourcePort = string.Empty;

    [ObservableProperty]
    private string newDraftConnectionTargetNodeId = string.Empty;

    [ObservableProperty]
    private string newDraftConnectionTargetPort = string.Empty;

    [ObservableProperty]
    private string selectedWorkflowDefinitionDraftConnectionId = string.Empty;

    [ObservableProperty]
    private bool isWorkflowDraftJsonAdvancedVisible;

    [ObservableProperty]
    private bool isWorkflowConnectionsAdvancedVisible;

    [ObservableProperty]
    private bool isWorkflowAddNodePanelVisible;

    [ObservableProperty]
    private bool isValidatingWorkflowDefinitionDraft;

    [ObservableProperty]
    private bool isSavingWorkflowDefinitionDraft;

    [ObservableProperty]
    private string workflowDefinitionValidationMessage = "Load definition to edit draft JSON.";

    [ObservableProperty]
    private string? workflowDefinitionValidationErrorMessage;

    [ObservableProperty]
    private bool isWorkflowDefinitionDraftDirty;

    [ObservableProperty]
    private bool hasWorkflowDefinitionRevisionConflict;

    private string originalWorkflowDefinitionJson = string.Empty;
    private string lastSuggestedNewDraftNodeInstanceId = string.Empty;
    private string lastSuggestedNewDraftNodeConfigJson = "{}";
    private string lastSuggestedNewDraftConnectionId = string.Empty;
    private int workflowDefinitionLoadVersion = 0;

    [ObservableProperty]
    private bool isLoadingRuns;

    [ObservableProperty]
    private bool isCancellingRun;

    [ObservableProperty]
    private WorkflowRunListItemViewModel? selectedRun;

    [ObservableProperty]
    private string runMessage = "No runs loaded.";

    [ObservableProperty]
    private string? runErrorMessage;

    [ObservableProperty]
    private bool isLoadingNodeRuns;

    [ObservableProperty]
    private string nodeRunMessage = "Select a run to load node status.";

    [ObservableProperty]
    private string? nodeRunErrorMessage;

    [ObservableProperty]
    private bool isRuntimeEventStreamRunning;

    [ObservableProperty]
    private bool isRuntimeEventStreamConnected;

    [ObservableProperty]
    private string runtimeEventStreamMessage = "Event stream disconnected.";

    [ObservableProperty]
    private string? runtimeEventStreamErrorMessage;

    [ObservableProperty]
    private long? lastRuntimeEventSequenceNumber;

    [ObservableProperty]
    private string logWorkflowRunIdFilter = string.Empty;

    [ObservableProperty]
    private string logNodeRunIdFilter = string.Empty;

    [ObservableProperty]
    private string logEventTypeFilter = string.Empty;

    [ObservableProperty]
    private string runtimeEventAfterSequenceNumberFilter = string.Empty;

    [ObservableProperty]
    private string runtimeEventLimitFilter = "100";

    [ObservableProperty]
    private bool isLoadingRuntimeEventLog;

    [ObservableProperty]
    private string runtimeEventLogMessage = "No runtime events loaded.";

    [ObservableProperty]
    private string? runtimeEventLogErrorMessage;

    [ObservableProperty]
    private bool isLoadingAuditEventLog;

    [ObservableProperty]
    private string auditEventLogMessage = "No audit events loaded.";

    [ObservableProperty]
    private string? auditEventLogErrorMessage;

    [ObservableProperty]
    private bool isLoadingTableRefs;

    [ObservableProperty]
    private string tableRefMessage = "Select a run to load table refs.";

    [ObservableProperty]
    private string? tableRefErrorMessage;

    [ObservableProperty]
    private bool isLoadingDataPreview;

    [ObservableProperty]
    private string dataPreviewMessage =
        "Select a run and workflow node to load data preview.";

    [ObservableProperty]
    private string? dataPreviewErrorMessage;

    [ObservableProperty]
    private string sharedPublicationShareNameFilter = string.Empty;

    [ObservableProperty]
    private string sharedPublicationLimitFilter = "100";

    [ObservableProperty]
    private bool isLoadingSharedPublications;

    [ObservableProperty]
    private SharedPublicationListItemViewModel? selectedSharedPublication;

    [ObservableProperty]
    private string sharedPublicationMessage = "No shared publications loaded.";

    [ObservableProperty]
    private string? sharedPublicationErrorMessage;

    [ObservableProperty]
    private string sharedPublicationVersionShareNameFilter = string.Empty;

    [ObservableProperty]
    private string sharedPublicationVersionLimitFilter = "100";

    [ObservableProperty]
    private bool isLoadingSharedPublicationVersions;

    [ObservableProperty]
    private string sharedPublicationVersionMessage =
        "Select or enter a share name to load versions.";

    [ObservableProperty]
    private string? sharedPublicationVersionErrorMessage;

    [ObservableProperty]
    private string currentLanguageCode = SupportedLanguage.Default.Code;

    [ObservableProperty]
    private string currentThemeVariant = PersistedUiSettings.SystemThemeVariant;

    [ObservableProperty]
    private ShellPageKey selectedShellPageKey = ShellPageKey.Workflows;

    [ObservableProperty]
    private int selectedShellPageIndex;

    public bool CanUseEngineActions =>
        ConnectionStatus == ConnectionStatus.Connected
        && !string.IsNullOrWhiteSpace(BaseUrl)
        && !string.IsNullOrWhiteSpace(Token)
        && !IsAuthenticationFailed;

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

    public ObservableCollection<LanguageMenuItemViewModel> Languages { get; } = new();

    public ObservableCollection<ThemeMenuItemViewModel> Themes { get; } = new();

    public ObservableCollection<ShellNavigationItemViewModel> ShellNavigationItems { get; } =
        new();

    public ShellNavigationItemViewModel WorkflowsNavigationItem =>
        GetShellNavigationItem(ShellPageKey.Workflows);

    public ShellNavigationItemViewModel RunsNavigationItem =>
        GetShellNavigationItem(ShellPageKey.Runs);

    public ShellNavigationItemViewModel DataNavigationItem =>
        GetShellNavigationItem(ShellPageKey.Data);

    public ShellNavigationItemViewModel LogsNavigationItem =>
        GetShellNavigationItem(ShellPageKey.Logs);

    public ShellNavigationItemViewModel SettingsNavigationItem =>
        GetShellNavigationItem(ShellPageKey.Settings);

    public ShellNavigationItemViewModel SelectedShellNavigationItem =>
        GetShellNavigationItem(SelectedShellPageKey);

    public ShellPageContentKey SelectedShellPageContentKey =>
        SelectedShellNavigationItem.ContentKey;

    public ObservableCollection<WorkflowListItemViewModel> Workflows { get; } = new();

    public ObservableCollection<WorkflowRunListItemViewModel> Runs { get; } = new();

    public ObservableCollection<NodeRunListItemViewModel> NodeRuns { get; } = new();

    public ObservableCollection<NodeDefinitionListItemViewModel> NodeDefinitions { get; } =
        new();

    public ObservableCollection<WorkflowDefinitionNodeListItemViewModel>
        WorkflowDefinitionDraftNodes { get; } = new();

    public ObservableCollection<NodeConfigEditableFieldInputViewModel>
        SelectedNodeConfigEditableInputFields { get; } = new();

    public ObservableCollection<RuntimeEventListItemViewModel> RuntimeEvents { get; } = new();

    public ObservableCollection<RuntimeEventListItemViewModel> RuntimeEventLogEntries { get; } = new();

    public ObservableCollection<AuditEventListItemViewModel> AuditEvents { get; } = new();

    public ObservableCollection<TableRefListItemViewModel> TableRefs { get; } = new();

    public ObservableCollection<TableDataPreviewColumnViewModel> DataPreviewColumns { get; } = new();

    public ObservableCollection<TableDataPreviewRowViewModel> DataPreviewRows { get; } =
        new();

    public ObservableCollection<SharedPublicationListItemViewModel> SharedPublications { get; } =
        new();

    public ObservableCollection<SharedPublicationListItemViewModel> SharedPublicationVersions { get; } =
        new();

    private DisplayTextFormatter DisplayTextFormatter => new(_localizationService);

    public bool IsChecking => ConnectionStatus == ConnectionStatus.Connecting;

    public bool HasError => !string.IsNullOrWhiteSpace(ErrorMessage);

    public bool HasWorkflowError => !string.IsNullOrWhiteSpace(WorkflowErrorMessage);

    public bool IsWorkflowBusy => IsLoadingWorkflows || IsStartingWorkflow || IsCreatingWorkflow;

    public bool HasLastStartedRun => !string.IsNullOrWhiteSpace(LastStartedRunId);

    public bool HasWorkflowDefinition => WorkflowDefinitionDetail is not null;

    public bool HasWorkflowDefinitionError =>
        !string.IsNullOrWhiteSpace(WorkflowDefinitionErrorMessage);

    public bool HasNodeDefinitionCatalogError =>
        !string.IsNullOrWhiteSpace(NodeDefinitionCatalogErrorMessage);

    public bool HasNodeDefinitions => NodeDefinitions.Count > 0;

    public bool HasNodeDefinitionCatalogEmptyState =>
        !IsLoadingNodeDefinitions && !HasNodeDefinitions;

    public bool HasSelectedWorkflowDefinitionNode => SelectedWorkflowDefinitionNode is not null;

    public bool HasNoSelectedWorkflowDefinitionNode => SelectedWorkflowDefinitionNode is null;

    public bool HasSelectedNodeConfigEditableInputFields =>
        SelectedNodeConfigEditableInputFields.Count > 0;

    public string SelectedNodeConfigDraftSummaryText =>
        SelectedNodeConfigEditableDraftMessage;

    public string? RefreshNodeDefinitionsDisabledReasonText
    {
        get
        {
            if (IsLoadingNodeDefinitions)
            {
                return T("action.disabled.busy");
            }

            if (!CanUseEngineActions)
            {
                return T("action.disabled.engine_not_connected");
            }

            return null;
        }
    }

    public bool IsWorkflowDefinitionDraftBusy =>
        IsValidatingWorkflowDefinitionDraft || IsSavingWorkflowDefinitionDraft;

    public bool HasWorkflowDefinitionValidationError =>
        !string.IsNullOrWhiteSpace(WorkflowDefinitionValidationErrorMessage);

    public bool HasWorkflowDefinitionDraft => !string.IsNullOrWhiteSpace(WorkflowDefinitionDraftJson);

    public bool HasWorkflowDefinitionDraftStructure =>
        WorkflowDefinitionDraftStructure?.IsSupported == true;

    public int WorkflowDefinitionDraftNodeCount =>
        WorkflowDefinitionDraftStructure?.NodeCount ?? 0;

    public string WorkflowDefinitionDraftNodeCountText =>
        DisplayTextFormatter.FormatNodeCount(WorkflowDefinitionDraftNodes.Count);

    public int WorkflowDefinitionBatchSelectedNodeCount =>
        WorkflowDefinitionDraftNodes.Count(node => node.IsBatchSelected);

    public string WorkflowDefinitionBatchSelectedNodeCountText =>
        F(
            "definition.batch_selected_nodes",
            WorkflowDefinitionBatchSelectedNodeCount);

    public int WorkflowDefinitionDraftConnectionCount =>
        WorkflowDefinitionDraftStructure?.ConnectionCount ?? 0;

    public string WorkflowDefinitionDraftConnectionCountText =>
        DisplayTextFormatter.FormatConnectionCount(WorkflowDefinitionDraftConnectionCount);

    public bool HasWorkflowDefinitionDraftStructureWarnings =>
        WorkflowDefinitionDraftStructure?.Warnings.Count > 0;

    public bool IsRunBusy => IsLoadingRuns || IsCancellingRun;

    public bool HasRunError => !string.IsNullOrWhiteSpace(RunErrorMessage);

    public bool IsNodeRunBusy => IsLoadingNodeRuns;

    public bool HasNodeRunError => !string.IsNullOrWhiteSpace(NodeRunErrorMessage);

    public bool HasRuntimeEventStreamError =>
        !string.IsNullOrWhiteSpace(RuntimeEventStreamErrorMessage);

    public bool HasRuntimeEvents => RuntimeEvents.Count > 0;

    public bool HasRuntimeEventLogError =>
        !string.IsNullOrWhiteSpace(RuntimeEventLogErrorMessage);

    public bool HasAuditEventLogError =>
        !string.IsNullOrWhiteSpace(AuditEventLogErrorMessage);

    public bool IsLogBusy => IsLoadingRuntimeEventLog || IsLoadingAuditEventLog;

    public bool HasTableRefError => !string.IsNullOrWhiteSpace(TableRefErrorMessage);

    public bool HasDataPreviewError =>
        !string.IsNullOrWhiteSpace(DataPreviewErrorMessage);

    public bool HasDataPreviewColumns => DataPreviewColumns.Count > 0;

    public bool HasDataPreviewRows => DataPreviewRows.Count > 0;

    public bool HasSharedPublicationError =>
        !string.IsNullOrWhiteSpace(SharedPublicationErrorMessage);

    public bool HasSharedPublicationVersionError =>
        !string.IsNullOrWhiteSpace(SharedPublicationVersionErrorMessage);

    public bool IsDataBusy =>
        IsLoadingTableRefs || IsLoadingSharedPublications || IsLoadingSharedPublicationVersions;

    public bool IsDataPreviewBusy => IsLoadingDataPreview;

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

    public string ConnectionBaseUrlText => T("connection.base_url");

    public string ConnectionTokenText => T("connection.token");

    public string ConnectionStatusText => T("connection.status");

    public string ConnectionEventsText => T("connection.events");

    public string CheckConnectionText => T("connection.check");

    public string StreamText => T("connection.stream");

    public string StopText => T("connection.stop");

    public string ExecutionTabText => T("tab.execution");

    public string DefinitionTabText => T("tab.definition");

    public string LogsTabText => T("tab.logs");

    public string DataTabText => T("tab.data");

    public string WorkflowsSectionText => T("workflow.section");

    public string RefreshText => T("common.refresh");

    public string CloseText => T("common.close");

    public string RunText => T("workflow.run");

    public string CreateText => T("workflow.create");

    public string WorkflowNameWatermarkText => T("workflow.name_watermark");

    public string RunsSectionText => T("runs.section");

    public string CancelText => T("runs.cancel");

    public string CancelConfirmTitleText => T("runs.cancel_confirm_title");

    public string CancelConfirmMessageText => T("runs.cancel_confirm_message");

    public string NodeRunsSectionText => T("node_runs.section");

    public string WorkflowDefinitionSectionText => T("definition.section");

    public string DetailsText => T("definition.details");

    public string NameLabelText => T("definition.name");

    public string VersionLabelText => T("definition.version");

    public string RevisionLabelText => T("definition.revision");

    public string StatusLabelText => T("definition.status");

    public string HashLabelText => T("definition.hash");

    public string UpdatedLabelText => T("definition.updated");

    public string NodesSectionText => T("definition.nodes");

    public string WorkflowNodesSectionText => T("definition.workflow_nodes");

    public string NodeConfigSectionText => T("definition.node_config");

    public string ApplyNodeConfigText => T("definition.apply_node_config");

    public string ApplyNodeDisplayNameText => T("definition.apply_node_display_name");

    public string StructuredEditSectionText => T("definition.structured_edit");

    public string AddNodeText => T("definition.add_node");

    public string CopyNodeText => T("definition.copy_node");

    public string DeleteNodeText => T("definition.delete_node");

    public string DeleteSelectedNodesText => T("definition.delete_selected_nodes");

    public string MoveNodeUpText => T("definition.move_node_up");

    public string MoveNodeDownText => T("definition.move_node_down");

    public string NodeActionsSectionText => T("definition.node_actions");

    public string DataPreviewSectionText => T("definition.data_preview");

    public string DataPreviewEmptyText => T("definition.data_preview_empty");

    public string DataPreviewPendingText => T("definition.data_preview_pending");

    public string DataPreviewRefreshText => T("definition.data_preview_refresh");

    public string PreviewSelectedNodeText => T("definition.preview_selected_node");

    public string NodeInstanceIdText => T("definition.node_instance_id");

    public string NodeTypeText => T("definition.node_type");

    public string NodeVersionText => T("definition.node_version");

    public string DisplayNameText => T("definition.display_name");

    public string ConfigJsonText => T("definition.config_json");

    public string ConnectionsSectionText => T("definition.connections");

    public string ShowConnectionsText => IsWorkflowConnectionsAdvancedVisible
        ? T("definition.hide_connections")
        : T("definition.show_connections");

    public string AddConnectionText => T("definition.add_connection");

    public string DeleteConnectionText => T("definition.delete_connection");

    public string ConnectionIdText => T("definition.connection_id");

    public string SourceNodeText => T("definition.source_node");

    public string SourcePortText => T("definition.source_port");

    public string TargetNodeText => T("definition.target_node");

    public string TargetPortText => T("definition.target_port");

    public string NodeCatalogSectionText => T("node_catalog.section");

    public string NodeText => T("node_catalog.node");

    public string NodeCatalogEmptyStateText => T("node_catalog.empty_state");

    public string InputsText => T("node_catalog.inputs");

    public string OutputsText => T("node_catalog.outputs");

    public string ModeText => T("node_catalog.mode");

    public string TimeoutText => T("node_catalog.timeout");

    public string DraftJsonSectionText => T("definition.draft_json");

    public string ShowAdvancedDraftJsonText => IsWorkflowDraftJsonAdvancedVisible
        ? T("definition.hide_draft_json")
        : T("definition.show_draft_json");

    public string ValidateText => T("definition.validate");

    public string SaveText => T("definition.save");

    public string WorkflowRunFilterText => T("logs.workflow_run");

    public string RunIdWatermarkText => T("logs.run_id_watermark");

    public string NodeRunFilterText => T("logs.node_run");

    public string NodeRunIdWatermarkText => T("logs.node_run_id_watermark");

    public string EventTypeFilterText => T("logs.event_type");

    public string AfterFilterText => T("logs.after");

    public string SequenceWatermarkText => T("logs.sequence_watermark");

    public string RuntimeText => T("logs.runtime");

    public string AuditText => T("logs.audit");

    public string LimitText => T("common.limit");

    public string RuntimeEventsSectionText => T("logs.runtime_events");

    public string AuditEventsSectionText => T("logs.audit_events");

    public string TableRefsSectionText => T("data.table_refs");

    public string ShareText => T("data.share");

    public string ShareNameWatermarkText => T("data.share_name_watermark");

    public string VersionsText => T("data.versions");

    public async Task LoadConnectionSettingsAsync(
        CancellationToken cancellationToken = default)
    {
        await TryLoadConnectionSettingsAsync(cancellationToken);
    }

    public async Task LoadConnectionSettingsAndCheckConnectionAsync(
        CancellationToken cancellationToken = default)
    {
        var loaded = await TryLoadConnectionSettingsAsync(cancellationToken);
        if (!loaded || !CanCheckConnection())
        {
            return;
        }

        await CheckConnectionCoreAsync(cancellationToken);
        if (ConnectionStatus == ConnectionStatus.Connected
            && runtimeEventStreamAutoConnect
            && !string.IsNullOrWhiteSpace(Token)
            && CanStartRuntimeEventStream())
        {
            await StartRuntimeEventStreamAsync();
        }
    }

    private async Task<bool> TryLoadConnectionSettingsAsync(
        CancellationToken cancellationToken)
    {
        try
        {
            var settings = await _connectionSettingsStore.LoadAsync(cancellationToken);
            BaseUrl = settings.LastSuccessfulBaseUrl;
            Token = settings.Token;
            runtimeEventStreamAutoConnect = settings.RuntimeEventStreamAutoConnect;
            return true;
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception ex)
        {
            ErrorMessage = F("format.connection_settings_load_failed", ex.Message);
            return false;
        }
    }

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

    private bool CanCheckConnection()
    {
        return !string.IsNullOrWhiteSpace(BaseUrl)
            && ConnectionStatus != ConnectionStatus.Connecting;
    }

    private bool CanRefreshWorkflows()
    {
        return CanUseEngineActions && !IsWorkflowBusy;
    }

    private bool CanStartSelectedWorkflow()
    {
        return CanUseEngineActions
            && SelectedWorkflow is not null
            && IsActiveWorkflowStatus(SelectedWorkflow.Status)
            && !IsWorkflowBusy;
    }

    private bool CanPreviewSelectedWorkflowNode()
    {
        return CanUseEngineActions
            && SelectedWorkflow is not null
            && IsActiveWorkflowStatus(SelectedWorkflow.Status)
            && WorkflowDefinitionDetail is not null
            && SelectedWorkflowDefinitionNode is not null
            && !IsWorkflowBusy
            && !IsDataPreviewBusy;
    }

    private bool CanCreateTemplateWorkflow()
    {
        return CanUseEngineActions
            && !IsWorkflowBusy
            && !string.IsNullOrWhiteSpace(NewWorkflowName);
    }

    private bool CanLoadSelectedWorkflowDefinition()
    {
        return CanUseEngineActions
            && SelectedWorkflow is not null
            && !IsLoadingWorkflowDefinition;
    }

    private bool CanRefreshNodeDefinitions()
    {
        return CanUseEngineActions && !IsLoadingNodeDefinitions;
    }

    private bool CanValidateWorkflowDefinitionDraft()
    {
        return CanUseEngineActions && HasWorkflowDefinitionDraft && !IsWorkflowDefinitionDraftBusy;
    }

    private bool CanApplySelectedNodeConfigDraft()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && SelectedWorkflowDefinitionNode is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict
            && HasSelectedNodeConfigEditableInputFields;
    }

    private bool CanApplySelectedNodeDisplayNameDraft()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && SelectedWorkflowDefinitionNode is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict
            && !string.Equals(
                SelectedNodeDisplayNameDraft.Trim(),
                SelectedWorkflowDefinitionNode.DisplayName,
                StringComparison.Ordinal);
    }

    private bool CanAddWorkflowDefinitionDraftNode()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict
            && !string.IsNullOrWhiteSpace(NewDraftNodeInstanceId)
            && !string.IsNullOrWhiteSpace(NewDraftNodeType)
            && !string.IsNullOrWhiteSpace(NewDraftNodeVersion)
            && !string.IsNullOrWhiteSpace(NewDraftNodeConfigJson);
    }

    private bool CanOpenWorkflowAddNodePanel()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict;
    }

    private bool CanDeleteWorkflowDefinitionDraftNode()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && SelectedWorkflowDefinitionNode is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict
            && FindDraftNode(SelectedWorkflowDefinitionNode.NodeInstanceId) is not null;
    }

    private bool CanDeleteSelectedWorkflowDefinitionDraftNodes()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict
            && WorkflowDefinitionDraftNodes.Any(node =>
                node.IsBatchSelected
                && FindDraftNode(node.NodeInstanceId) is not null);
    }

    private bool CanCopyWorkflowDefinitionDraftNode()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && SelectedWorkflowDefinitionNode is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict
            && FindDraftNode(SelectedWorkflowDefinitionNode.NodeInstanceId) is not null;
    }

    private bool CanMoveSelectedWorkflowDefinitionDraftNodeUp()
    {
        return CanMoveSelectedWorkflowDefinitionDraftNode(offset: -1);
    }

    private bool CanMoveSelectedWorkflowDefinitionDraftNodeDown()
    {
        return CanMoveSelectedWorkflowDefinitionDraftNode(offset: 1);
    }

    private bool CanMoveSelectedWorkflowDefinitionDraftNode(int offset)
    {
        if (!CanUseEngineActions ||
            WorkflowDefinitionDetail is null ||
            SelectedWorkflowDefinitionNode is null ||
            !HasWorkflowDefinitionDraft ||
            IsWorkflowDefinitionDraftBusy ||
            HasWorkflowDefinitionRevisionConflict)
        {
            return false;
        }

        var index = WorkflowDefinitionDraftNodes.IndexOf(SelectedWorkflowDefinitionNode);
        var targetIndex = index + offset;
        return index >= 0 &&
            targetIndex >= 0 &&
            targetIndex < WorkflowDefinitionDraftNodes.Count;
    }

    private bool CanAddWorkflowDefinitionDraftConnection()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict
            && !string.IsNullOrWhiteSpace(NewDraftConnectionId)
            && !string.IsNullOrWhiteSpace(NewDraftConnectionSourceNodeId)
            && !string.IsNullOrWhiteSpace(NewDraftConnectionSourcePort)
            && !string.IsNullOrWhiteSpace(NewDraftConnectionTargetNodeId)
            && !string.IsNullOrWhiteSpace(NewDraftConnectionTargetPort);
    }

    private bool CanDeleteWorkflowDefinitionDraftConnection()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict
            && !string.IsNullOrWhiteSpace(SelectedWorkflowDefinitionDraftConnectionId);
    }

    private bool CanSaveWorkflowDefinitionDraft()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && HasWorkflowDefinitionDraft
            && IsWorkflowDefinitionDraftDirty
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict;
    }

    private bool CanRefreshRuns()
    {
        return CanUseEngineActions && !IsRunBusy;
    }

    private bool CanCancelSelectedRunCore()
    {
        return CanUseEngineActions
            && SelectedRun is not null
            && IsCancelableRunStatus(SelectedRun.Status)
            && !IsRunBusy;
    }

    public bool CanUseCancelSelectedRunAction => CanCancelSelectedRunCore();

    public string? CancelSelectedRunDisabledReasonText
    {
        get
        {
            if (IsRunBusy)
            {
                return T("action.disabled.busy");
            }

            if (!CanUseEngineActions)
            {
                return T("action.disabled.engine_not_connected");
            }

            if (SelectedRun is null)
            {
                return T("action.disabled.no_run_selected");
            }

            if (string.IsNullOrWhiteSpace(SelectedRun.Status) || SelectedRun.Status == "UNKNOWN")
            {
                return T("action.disabled.run_status_unknown");
            }

            if (IsTerminalRunStatus(SelectedRun.Status))
            {
                return T("action.disabled.run_terminal");
            }

            if (!IsCancelableRunStatus(SelectedRun.Status))
            {
                return T("action.disabled.run_not_running");
            }

            return null;
        }
    }

    private bool CanRefreshNodeRuns()
    {
        return CanUseEngineActions && SelectedRun is not null && !IsNodeRunBusy;
    }

    private bool CanStartRuntimeEventStream()
    {
        return !IsRuntimeEventStreamRunning && !string.IsNullOrWhiteSpace(BaseUrl);
    }

    private bool CanStopRuntimeEventStream()
    {
        return IsRuntimeEventStreamRunning;
    }

    private bool CanRefreshRuntimeEventLog()
    {
        return CanUseEngineActions && !IsLoadingRuntimeEventLog;
    }

    private bool CanRefreshAuditEvents()
    {
        return CanUseEngineActions && !IsLoadingAuditEventLog;
    }

    private bool CanRefreshTableRefs()
    {
        return CanUseEngineActions && SelectedRun is not null && !IsLoadingTableRefs;
    }

    private bool CanRefreshSelectedWorkflowNodeDataPreview()
    {
        return CanUseEngineActions
            && SelectedRun is not null
            && SelectedWorkflowDefinitionNode is not null
            && !IsLoadingDataPreview;
    }

    private bool CanRefreshSharedPublications()
    {
        return CanUseEngineActions && !IsLoadingSharedPublications;
    }

    private bool CanRefreshSharedPublicationVersions()
    {
        return CanUseEngineActions
            && !IsLoadingSharedPublicationVersions
            && (NormalizeFilter(SharedPublicationVersionShareNameFilter) is not null
                || SelectedSharedPublication is not null);
    }

    [RelayCommand(CanExecute = nameof(CanCheckConnection))]
    private async Task CheckConnectionAsync()
    {
        await CheckConnectionCoreAsync(_shutdown.Token);
    }

    private async Task CheckConnectionCoreAsync(
        CancellationToken cancellationToken)
    {
        ConnectionStatus = ConnectionStatus.Connecting;
        StatusMessage = T("status.checking_enginehost");
        ErrorMessage = null;

        var settings = new EngineHostConnectionSettings
        {
            BaseUrl = BaseUrl,
            Token = Token,
        };

        var result = await _healthClient.CheckAsync(settings, cancellationToken);

        if (result.IsHealthy)
        {
            ConnectionStatus = ConnectionStatus.Connected;
            StatusMessage = LocalizeHealthStatusMessage(result);
            ErrorMessage = null;
            await SaveConnectionSettingsAsync(settings);
            await RefreshNodeDefinitionsAfterHealthyConnectionAsync();
            await RefreshWorkflowsAfterHealthyConnectionAsync();
            return;
        }

        ConnectionStatus = ConnectionStatus.Error;
        StatusMessage = LocalizeHealthStatusMessage(result);
        ErrorMessage = LocalizeHealthErrorMessage(result.ErrorMessage);
    }

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

    [RelayCommand(CanExecute = nameof(CanRefreshWorkflows))]
    private async Task RefreshWorkflowsAsync()
    {
        IsLoadingWorkflows = true;
        WorkflowMessage = T("workflow.loading");
        WorkflowErrorMessage = null;

        var response = await _apiClient.ListWorkflowsAsync(
            BuildSettings(),
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            var previousWorkflowId = SelectedWorkflow?.WorkflowId;
            Workflows.Clear();
            foreach (var workflow in response.Data)
            {
                Workflows.Add(new WorkflowListItemViewModel(workflow));
            }

            SelectedWorkflow = Workflows.FirstOrDefault(
                workflow => workflow.WorkflowId == previousWorkflowId)
                ?? Workflows.FirstOrDefault();
            WorkflowMessage = F("format.loaded_workflows", Workflows.Count);
            IsLoadingWorkflows = false;
            return;
        }

        WorkflowMessage = T("workflow.refresh_failed");
        WorkflowErrorMessage = DescribeError(response);
        IsLoadingWorkflows = false;
    }

    [RelayCommand(CanExecute = nameof(CanCreateTemplateWorkflow))]
    private async Task CreateTemplateWorkflowAsync()
    {
        var name = NewWorkflowName.Trim();
        if (string.IsNullOrWhiteSpace(name))
        {
            WorkflowMessage = T("workflow.creation_rejected");
            WorkflowErrorMessage = T("workflow.name_required");
            return;
        }

        IsCreatingWorkflow = true;
        WorkflowMessage = F("format.creating_workflow", name);
        WorkflowErrorMessage = null;

        using var definition = TemplateWorkflowDefinitions.CreateGeneratedTable(
            T("workflow.template.generate_rows_display_name"),
            T("workflow.template.keep_amount_gt_one_display_name"));
        var response = await _apiClient.CreateWorkflowAsync(
            BuildSettings(),
            name,
            definition.RootElement,
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            WorkflowMessage = F("format.created_workflow", response.Data.Name);
            IsCreatingWorkflow = false;
            await RefreshWorkflowsSelectingAsync(response.Data.WorkflowId);
            return;
        }

        WorkflowMessage = T("workflow.creation_failed");
        WorkflowErrorMessage = DescribeError(response);
        IsCreatingWorkflow = false;
    }

    [RelayCommand(CanExecute = nameof(CanLoadSelectedWorkflowDefinition))]
    private async Task LoadSelectedWorkflowDefinitionAsync()
    {
        if (SelectedWorkflow is null)
        {
            return;
        }

        var workflowId = SelectedWorkflow.WorkflowId;
        var requestVersion = ++workflowDefinitionLoadVersion;
        IsLoadingWorkflowDefinition = true;
        WorkflowDefinitionMessage = F(
            "format.loading_definition_for",
            SelectedWorkflow.Name);
        WorkflowDefinitionErrorMessage = null;

        try
        {
            var workflowResponse = await _apiClient.GetWorkflowAsync(
                BuildSettings(),
                workflowId,
                _shutdown.Token);

            if (SelectedWorkflow?.WorkflowId != workflowId || requestVersion != workflowDefinitionLoadVersion)
            {
                return;
            }

            if (!workflowResponse.Ok || workflowResponse.Data is null)
            {
                WorkflowDefinitionDetail = null;
                SelectedWorkflowDefinitionNode = null;
                WorkflowDefinitionMessage = T("definition.load_failed");
                WorkflowDefinitionErrorMessage = DescribeError(workflowResponse);
                return;
            }

            var revisionsResponse = await _apiClient.ListWorkflowRevisionsAsync(
                BuildSettings(),
                workflowId,
                _shutdown.Token);

            if (SelectedWorkflow?.WorkflowId != workflowId || requestVersion != workflowDefinitionLoadVersion)
            {
                return;
            }

            if (!revisionsResponse.Ok || revisionsResponse.Data is null)
            {
                WorkflowDefinitionDetail = null;
                SelectedWorkflowDefinitionNode = null;
                WorkflowDefinitionMessage = T("definition.revisions_load_failed");
                WorkflowDefinitionErrorMessage = DescribeError(revisionsResponse);
                return;
            }

            WorkflowDefinitionDetail = new WorkflowDefinitionDetailViewModel(
                workflowResponse.Data,
                revisionsResponse.Data,
                DisplayTextFormatter);
            SelectedWorkflowDefinitionNode =
                WorkflowDefinitionDetail.Nodes.FirstOrDefault();
            originalWorkflowDefinitionJson = WorkflowDefinitionDetail.RawDefinitionJson;
            WorkflowDefinitionDraftJson = originalWorkflowDefinitionJson;
            IsWorkflowDefinitionDraftDirty = false;
            HasWorkflowDefinitionRevisionConflict = false;
            WorkflowDefinitionValidationMessage = T("definition.draft_loaded");
            WorkflowDefinitionValidationErrorMessage = null;
            WorkflowDefinitionMessage =
                F(
                    "format.loaded_workflow_definition",
                    WorkflowDefinitionDetail.Name,
                    WorkflowDefinitionDetail.VersionText);
        }
        finally
        {
            if (requestVersion == workflowDefinitionLoadVersion)
            {
                IsLoadingWorkflowDefinition = false;
            }
        }
    }

    [RelayCommand(CanExecute = nameof(CanRefreshNodeDefinitions))]
    private async Task RefreshNodeDefinitionsAsync()
    {
        var requestVersion = ++nodeDefinitionsLoadVersion;
        IsLoadingNodeDefinitions = true;
        NodeDefinitionCatalogMessage = T("node_catalog.loading");
        NodeDefinitionCatalogErrorMessage = null;

        try
        {
            var response = await _apiClient.ListNodeDefinitionsAsync(
                BuildSettings(),
                _shutdown.Token);

            if (requestVersion != nodeDefinitionsLoadVersion)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                SelectedNewDraftNodeDefinition = null;
                NodeDefinitions.Clear();
                foreach (var definition in response.Data
                    .OrderBy(definition => definition.DisplayName)
                    .ThenBy(definition => definition.NodeType)
                    .ThenBy(definition => definition.NodeVersion))
                {
                    NodeDefinitions.Add(new NodeDefinitionListItemViewModel(
                        definition,
                        DisplayTextFormatter));
                }

                OnPropertyChanged(nameof(HasNodeDefinitions));
                OnPropertyChanged(nameof(HasNodeDefinitionCatalogEmptyState));
                RefreshSelectedNodeConfigDraftState();
                NodeDefinitionCatalogMessage =
                    F("format.loaded_node_definitions", NodeDefinitions.Count);
                return;
            }

            NodeDefinitionCatalogMessage = T("node_catalog.refresh_failed");
            NodeDefinitionCatalogErrorMessage = DescribeError(response);
            SelectedNewDraftNodeDefinition = null;
            OnPropertyChanged(nameof(HasNodeDefinitions));
            OnPropertyChanged(nameof(HasNodeDefinitionCatalogEmptyState));
            RefreshSelectedNodeConfigDraftState();
        }
        finally
        {
            if (requestVersion == nodeDefinitionsLoadVersion)
            {
                IsLoadingNodeDefinitions = false;
            }
        }
    }

    private async Task RefreshNodeDefinitionsAfterHealthyConnectionAsync()
    {
        if (HasNodeDefinitions || !CanRefreshNodeDefinitions())
        {
            return;
        }

        await RefreshNodeDefinitionsAsync();
    }

    private async Task RefreshWorkflowsAfterHealthyConnectionAsync()
    {
        if (Workflows.Count > 0 || !CanRefreshWorkflows())
        {
            return;
        }

        await RefreshWorkflowsAsync();
        if (CanLoadSelectedWorkflowDefinition())
        {
            await LoadSelectedWorkflowDefinitionAsync();
        }
    }

    [RelayCommand(CanExecute = nameof(CanValidateWorkflowDefinitionDraft))]
    private async Task ValidateWorkflowDefinitionDraftAsync()
    {
        if (string.IsNullOrWhiteSpace(WorkflowDefinitionDraftJson))
        {
            WorkflowDefinitionValidationMessage = T("definition.validation_rejected");
            WorkflowDefinitionValidationErrorMessage = T("definition.draft_required");
            return;
        }

        JsonElement definition;
        try
        {
            using var parsed = JsonDocument.Parse(WorkflowDefinitionDraftJson);
            definition = parsed.RootElement.Clone();
        }
        catch (JsonException ex)
        {
            WorkflowDefinitionValidationMessage = T("definition.draft_json_invalid");
            WorkflowDefinitionValidationErrorMessage = ex.Message;
            return;
        }

        IsValidatingWorkflowDefinitionDraft = true;
        WorkflowDefinitionValidationMessage = T("definition.validating_draft");
        WorkflowDefinitionValidationErrorMessage = null;

        var response = await _apiClient.ValidateWorkflowDraftAsync(
            BuildSettings(),
            definition,
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            WorkflowDefinitionValidationMessage = response.Data.Valid
                ? T("definition.draft_valid")
                : T("definition.draft_has_issues");
            WorkflowDefinitionValidationErrorMessage = FormatValidationIssues(response.Data);
            IsValidatingWorkflowDefinitionDraft = false;
            return;
        }

        WorkflowDefinitionValidationMessage = T("definition.validation_failed");
        WorkflowDefinitionValidationErrorMessage = DescribeError(response);
        IsValidatingWorkflowDefinitionDraft = false;
    }

    [RelayCommand(CanExecute = nameof(CanApplySelectedNodeConfigDraft))]
    private void ApplySelectedNodeConfigDraft()
    {
        if (SelectedWorkflowDefinitionNode is null)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_config_apply_failed");
            WorkflowDefinitionValidationErrorMessage =
                DisplayTextFormatter.FormatSelectedNodeConfigDraftMissingSelection();
            return;
        }

        var configResult = NodeConfigEditableFieldInputConfigBuilder.Build(
            SelectedWorkflowDefinitionNode.NodeInstanceId,
            SelectedNodeConfigEditableInputFields);
        if (!configResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_config_apply_failed");
            WorkflowDefinitionValidationErrorMessage =
                FormatNodeConfigApplyErrors(configResult);
            return;
        }

        using var config = JsonDocument.Parse(configResult.ConfigJson);
        var patchResult = NodeConfigDraftJsonPatcher.ApplyConfig(
            WorkflowDefinitionDraftJson,
            SelectedWorkflowDefinitionNode.NodeInstanceId,
            config.RootElement);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_config_apply_failed");
            WorkflowDefinitionValidationErrorMessage = patchResult.Warning;
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        WorkflowDefinitionValidationMessage = T("definition.node_config_applied");
        WorkflowDefinitionValidationErrorMessage = null;
    }

    [RelayCommand(CanExecute = nameof(CanApplySelectedNodeDisplayNameDraft))]
    private void ApplySelectedNodeDisplayNameDraft()
    {
        if (SelectedWorkflowDefinitionNode is null)
        {
            return;
        }

        var nodeInstanceId = SelectedWorkflowDefinitionNode.NodeInstanceId;
        var patchResult = WorkflowDefinitionDraftNodePatcher.UpdateDisplayName(
            WorkflowDefinitionDraftJson,
            nodeInstanceId,
            SelectedNodeDisplayNameDraft);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_display_name_apply_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        SelectWorkflowDefinitionDraftNode(nodeInstanceId);
        WorkflowDefinitionValidationMessage = T("definition.node_display_name_applied");
        WorkflowDefinitionValidationErrorMessage = null;
    }

    [RelayCommand(CanExecute = nameof(CanAddWorkflowDefinitionDraftNode))]
    private void AddWorkflowDefinitionDraftNode()
    {
        var autoWirePorts = TryGetAutoWirePorts();
        JsonElement config;
        try
        {
            using var parsed = JsonDocument.Parse(NewDraftNodeConfigJson);
            config = parsed.RootElement.Clone();
        }
        catch (JsonException)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_add_failed");
            WorkflowDefinitionValidationErrorMessage =
                T("definition.node_add_config_json_invalid");
            return;
        }

        var patchResult = WorkflowDefinitionDraftNodePatcher.AddNode(
            WorkflowDefinitionDraftJson,
            NewDraftNodeInstanceId,
            NewDraftNodeType,
            NewDraftNodeVersion,
            NewDraftNodeDisplayName,
            config,
            SelectedWorkflowDefinitionNode?.NodeInstanceId,
            autoWirePorts.InputPort,
            autoWirePorts.OutputPort);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_add_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        SelectWorkflowDefinitionDraftNode(NewDraftNodeInstanceId);
        WorkflowDefinitionValidationMessage =
            patchResult.AddedConnections.Count > 0
                ? T("definition.node_added_with_connections")
                : T("definition.node_added");
        WorkflowDefinitionValidationErrorMessage =
            FormatAutoWiredConnectionsMessage(
                patchResult.RemovedConnections,
                patchResult.AddedConnections);
        ResetNewDraftNodeInput();
        IsWorkflowAddNodePanelVisible = false;
    }

    [RelayCommand(CanExecute = nameof(CanOpenWorkflowAddNodePanel))]
    private void OpenWorkflowAddNodePanel()
    {
        IsWorkflowAddNodePanelVisible = true;
    }

    [RelayCommand]
    private void CloseWorkflowAddNodePanel()
    {
        IsWorkflowAddNodePanelVisible = false;
    }

    [RelayCommand(CanExecute = nameof(CanDeleteWorkflowDefinitionDraftNode))]
    private void DeleteWorkflowDefinitionDraftNode()
    {
        if (SelectedWorkflowDefinitionNode is null)
        {
            return;
        }

        var patchResult = WorkflowDefinitionDraftNodePatcher.DeleteNode(
            WorkflowDefinitionDraftJson,
            SelectedWorkflowDefinitionNode.NodeInstanceId);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_delete_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        WorkflowDefinitionValidationMessage =
            patchResult.RemovedConnections.Count > 0
                ? T("definition.node_deleted_with_connections")
                : T("definition.node_deleted");
        WorkflowDefinitionValidationErrorMessage =
            FormatRemovedConnectionsMessage(patchResult.RemovedConnections);
    }

    [RelayCommand(CanExecute = nameof(CanDeleteSelectedWorkflowDefinitionDraftNodes))]
    private void DeleteSelectedWorkflowDefinitionDraftNodes()
    {
        var selectedNodeIds = WorkflowDefinitionDraftNodes
            .Where(node => node.IsBatchSelected)
            .Select(node => node.NodeInstanceId)
            .ToArray();
        if (selectedNodeIds.Length == 0)
        {
            return;
        }

        var patchResult = WorkflowDefinitionDraftNodePatcher.DeleteNodes(
            WorkflowDefinitionDraftJson,
            selectedNodeIds);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_delete_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        WorkflowDefinitionValidationMessage =
            patchResult.RemovedConnections.Count > 0
                ? F(
                    "format.workflow_definition_nodes_deleted_with_connections",
                    selectedNodeIds.Length)
                : F("format.workflow_definition_nodes_deleted", selectedNodeIds.Length);
        WorkflowDefinitionValidationErrorMessage =
            FormatRemovedConnectionsMessage(patchResult.RemovedConnections);
    }

    [RelayCommand(CanExecute = nameof(CanCopyWorkflowDefinitionDraftNode))]
    private void CopyWorkflowDefinitionDraftNode()
    {
        if (SelectedWorkflowDefinitionNode is null)
        {
            return;
        }

        var patchResult = WorkflowDefinitionDraftNodePatcher.CopyNode(
            WorkflowDefinitionDraftJson,
            SelectedWorkflowDefinitionNode.NodeInstanceId);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_copy_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        if (!string.IsNullOrWhiteSpace(patchResult.AddedNodeInstanceId))
        {
            SelectWorkflowDefinitionDraftNode(patchResult.AddedNodeInstanceId);
        }

        WorkflowDefinitionValidationMessage = T("definition.node_copied");
        WorkflowDefinitionValidationErrorMessage = null;
    }

    [RelayCommand(CanExecute = nameof(CanMoveSelectedWorkflowDefinitionDraftNodeUp))]
    private void MoveSelectedWorkflowDefinitionDraftNodeUp()
    {
        MoveSelectedWorkflowDefinitionDraftNode(offset: -1);
    }

    [RelayCommand(CanExecute = nameof(CanMoveSelectedWorkflowDefinitionDraftNodeDown))]
    private void MoveSelectedWorkflowDefinitionDraftNodeDown()
    {
        MoveSelectedWorkflowDefinitionDraftNode(offset: 1);
    }

    private void MoveSelectedWorkflowDefinitionDraftNode(int offset)
    {
        if (SelectedWorkflowDefinitionNode is null)
        {
            return;
        }

        var nodeInstanceId = SelectedWorkflowDefinitionNode.NodeInstanceId;
        var patchResult = WorkflowDefinitionDraftNodePatcher.MoveNode(
            WorkflowDefinitionDraftJson,
            nodeInstanceId,
            offset);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_move_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        SelectWorkflowDefinitionDraftNode(nodeInstanceId);
        WorkflowDefinitionValidationMessage = T("definition.node_moved");
        WorkflowDefinitionValidationErrorMessage = null;
    }

    [RelayCommand(CanExecute = nameof(CanAddWorkflowDefinitionDraftConnection))]
    private void AddWorkflowDefinitionDraftConnection()
    {
        var patchResult = WorkflowDefinitionDraftConnectionPatcher.AddConnection(
            WorkflowDefinitionDraftJson,
            NewDraftConnectionId,
            NewDraftConnectionSourceNodeId,
            NewDraftConnectionSourcePort,
            NewDraftConnectionTargetNodeId,
            NewDraftConnectionTargetPort);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.connection_add_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        WorkflowDefinitionValidationMessage = T("definition.connection_added");
        WorkflowDefinitionValidationErrorMessage = null;
        ResetNewDraftConnectionInput();
    }

    [RelayCommand(CanExecute = nameof(CanDeleteWorkflowDefinitionDraftConnection))]
    private void DeleteWorkflowDefinitionDraftConnection()
    {
        var patchResult = WorkflowDefinitionDraftConnectionPatcher.DeleteConnection(
            WorkflowDefinitionDraftJson,
            SelectedWorkflowDefinitionDraftConnectionId);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.connection_delete_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        WorkflowDefinitionValidationMessage = T("definition.connection_deleted");
        WorkflowDefinitionValidationErrorMessage = null;
    }

    [RelayCommand(CanExecute = nameof(CanSaveWorkflowDefinitionDraft))]
    private async Task SaveWorkflowDefinitionDraftAsync()
    {
        if (WorkflowDefinitionDetail is null)
        {
            WorkflowDefinitionValidationMessage = T("definition.save_rejected");
            WorkflowDefinitionValidationErrorMessage = T("definition.load_before_saving");
            return;
        }

        JsonElement definition;
        try
        {
            using var parsed = JsonDocument.Parse(WorkflowDefinitionDraftJson);
            definition = parsed.RootElement.Clone();
        }
        catch (JsonException ex)
        {
            WorkflowDefinitionValidationMessage = T("definition.draft_json_invalid");
            WorkflowDefinitionValidationErrorMessage = ex.Message;
            return;
        }

        IsSavingWorkflowDefinitionDraft = true;
        WorkflowDefinitionValidationMessage = T("definition.saving_draft");
        WorkflowDefinitionValidationErrorMessage = null;

        try
        {
            var saved = await _apiClient.UpdateWorkflowAsync(
                BuildSettings(),
                WorkflowDefinitionDetail.WorkflowId,
                WorkflowDefinitionDetail.Name,
                definition,
                WorkflowDefinitionDetail.RevisionId,
                _shutdown.Token);

            if (saved.Ok && saved.Data is not null)
            {
                WorkflowDefinitionValidationMessage =
                    F("format.saved_workflow", saved.Data.Name, saved.Data.Version);
                IsWorkflowDefinitionDraftDirty = false;
                HasWorkflowDefinitionRevisionConflict = false;
                await RefreshWorkflowsSelectingAsync(saved.Data.WorkflowId);
                await LoadSelectedWorkflowDefinitionAsync();
                return;
            }

            if (saved.Error?.ErrorCode == "WORKFLOW_REVISION_CONFLICT")
            {
                HasWorkflowDefinitionRevisionConflict = true;
                WorkflowDefinitionValidationMessage = T("definition.save_failed");
                WorkflowDefinitionValidationErrorMessage = T("definition.revision_conflict");
                return;
            }

            WorkflowDefinitionValidationMessage = T("definition.save_failed");
            WorkflowDefinitionValidationErrorMessage = DescribeError(saved);
        }
        finally
        {
            IsSavingWorkflowDefinitionDraft = false;
        }
    }

    [RelayCommand(CanExecute = nameof(CanStartSelectedWorkflow))]
    private async Task StartSelectedWorkflowAsync()
    {
        if (SelectedWorkflow is null)
        {
            return;
        }

        IsStartingWorkflow = true;
        WorkflowMessage = F("format.starting_workflow", SelectedWorkflow.Name);
        WorkflowErrorMessage = null;
        LastStartedRunId = null;
        LastStartedRunStatus = null;

        var response = await _apiClient.StartWorkflowRunAsync(
            BuildSettings(),
            SelectedWorkflow.WorkflowId,
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            LastStartedRunId = response.Data.WorkflowRunId;
            LastStartedRunStatus = response.Data.Status;
            WorkflowMessage =
                F(
                    "format.started_run_with_status",
                    response.Data.WorkflowRunId,
                    response.Data.Status);
            IsStartingWorkflow = false;
            await TrackWorkflowRunUntilTerminalAsync(response.Data.WorkflowRunId);
            await SelectLatestReadableOutputNodeForRunAsync(response.Data.WorkflowRunId);
            if (CanRefreshSelectedWorkflowNodeDataPreview())
            {
                await RefreshSelectedWorkflowNodeDataPreviewAsync();
            }

            return;
        }

        WorkflowMessage = T("workflow.start_failed");
        WorkflowErrorMessage = DescribeError(response);
        IsStartingWorkflow = false;
    }

    [RelayCommand(CanExecute = nameof(CanPreviewSelectedWorkflowNode))]
    private async Task PreviewSelectedWorkflowNodeAsync()
    {
        if (SelectedWorkflow is null || SelectedWorkflowDefinitionNode is null)
        {
            return;
        }

        var targetNodeInstanceId = SelectedWorkflowDefinitionNode.NodeInstanceId;
        IsStartingWorkflow = true;
        WorkflowMessage = F("format.previewing_workflow_to_node", targetNodeInstanceId);
        WorkflowErrorMessage = null;
        DataPreviewMessage = F("format.previewing_workflow_to_node", targetNodeInstanceId);
        DataPreviewErrorMessage = null;
        LastStartedRunId = null;
        LastStartedRunStatus = null;

        var response = await _apiClient.StartWorkflowRunAsync(
            BuildSettings(),
            SelectedWorkflow.WorkflowId,
            "preview_to_node",
            targetNodeInstanceId,
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            LastStartedRunId = response.Data.WorkflowRunId;
            LastStartedRunStatus = response.Data.Status;
            WorkflowMessage =
                F(
                    "format.started_preview_run_with_status",
                    response.Data.WorkflowRunId,
                    response.Data.Status,
                    targetNodeInstanceId);
            IsStartingWorkflow = false;
            await RefreshSelectedWorkflowNodeDataPreviewAfterRunStartAsync(response.Data.WorkflowRunId);

            return;
        }

        WorkflowMessage = T("workflow.start_failed");
        WorkflowErrorMessage = DescribeError(response);
        DataPreviewMessage = T("data_preview.preview_failed");
        DataPreviewErrorMessage = DescribeError(response);
        IsStartingWorkflow = false;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshRuns))]
    private Task RefreshRunsAsync()
    {
        return LoadRunsAsync();
    }

    [RelayCommand(CanExecute = nameof(CanCancelSelectedRunCore))]
    private async Task CancelSelectedRunAsync()
    {
        if (SelectedRun is null)
        {
            return;
        }

        var workflowRunId = SelectedRun.WorkflowRunId;
        IsCancellingRun = true;
        RunMessage = F("format.cancelling_run", workflowRunId);
        RunErrorMessage = null;

        var response = await _apiClient.CancelRunAsync(
            BuildSettings(),
            workflowRunId,
            _shutdown.Token);

        IsCancellingRun = false;

        if (response.Ok)
        {
            var processStatus = response.Data?.Status;
            var cancelMessage = string.IsNullOrWhiteSpace(processStatus)
                ? F("format.cancel_requested", workflowRunId)
                : F("format.cancel_requested_with_status", workflowRunId, processStatus);
            await LoadRunsAsync(workflowRunId);
            if (!HasRunError)
            {
                RunMessage = cancelMessage;
            }

            return;
        }

        RunMessage = T("runs.cancel_failed");
        RunErrorMessage = DescribeError(response);
    }

    [RelayCommand(CanExecute = nameof(CanRefreshNodeRuns))]
    private async Task RefreshNodeRunsAsync()
    {
        await LoadNodeRunsForSelectedRunAsync();
    }

    [RelayCommand(CanExecute = nameof(CanStartRuntimeEventStream))]
    private async Task StartRuntimeEventStreamAsync()
    {
        var settings = BuildSettings();
        try
        {
            _runtimeEventStreamClient.BuildEventsUri(settings);
        }
        catch (InvalidOperationException ex)
        {
            RuntimeEventStreamMessage = T("events.stream_config_invalid");
            RuntimeEventStreamErrorMessage = ex.Message;
            return;
        }

        runtimeEventStreamAutoConnect = true;
        await SaveConnectionSettingsAsync(settings);
        RuntimeEventStreamErrorMessage = null;
        RuntimeEventStreamMessage = T("events.stream_connecting");
        RuntimeEvents.Clear();
        OnPropertyChanged(nameof(HasRuntimeEvents));
        LastRuntimeEventSequenceNumber = null;

        _runtimeEventStreamCancellation?.Cancel();
        _runtimeEventStreamCancellation?.Dispose();
        _runtimeEventStreamCancellation =
            CancellationTokenSource.CreateLinkedTokenSource(_shutdown.Token);
        IsRuntimeEventStreamRunning = true;
        IsRuntimeEventStreamConnected = false;
        _runtimeEventStreamTask = RunRuntimeEventStreamLoopAsync(
            _runtimeEventStreamCancellation.Token);
    }

    [RelayCommand(CanExecute = nameof(CanStopRuntimeEventStream))]
    private async Task StopRuntimeEventStreamAsync()
    {
        var cancellation = _runtimeEventStreamCancellation;
        var streamTask = _runtimeEventStreamTask;
        if (cancellation is null || streamTask is null)
        {
            return;
        }

        RuntimeEventStreamMessage = T("events.stream_stopping");
        cancellation.Cancel();

        try
        {
            await streamTask;
        }
        catch (OperationCanceledException)
        {
        }

        RuntimeEventStreamMessage = T("events.stream_stopped");
        RuntimeEventStreamErrorMessage = null;
        runtimeEventStreamAutoConnect = false;
        await SaveConnectionSettingsAsync(BuildSettings());
    }

    [RelayCommand(CanExecute = nameof(CanRefreshRuntimeEventLog), AllowConcurrentExecutions = true)]
    private async Task RefreshRuntimeEventLogAsync()
    {
        if (!TryParseRuntimeEventLogFilters(out var afterSequenceNumber, out var limit, out var error))
        {
            RuntimeEventLogMessage = T("logs.runtime_refresh_rejected");
            RuntimeEventLogErrorMessage = error;
            return;
        }

        var requestVersion = ++runtimeEventLogLoadVersion;
        IsLoadingRuntimeEventLog = true;
        RuntimeEventLogMessage = T("logs.loading_runtime_events");
        RuntimeEventLogErrorMessage = null;

        try
        {
            var response = await _apiClient.ListEventsAsync(
                BuildSettings(),
                afterSequenceNumber,
                NormalizeFilter(LogWorkflowRunIdFilter),
                NormalizeFilter(LogNodeRunIdFilter),
                NormalizeFilter(LogEventTypeFilter),
                limit,
                _shutdown.Token);

            if (requestVersion != runtimeEventLogLoadVersion)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                RuntimeEventLogEntries.Clear();
                foreach (var runtimeEvent in response.Data)
                {
                    RuntimeEventLogEntries.Add(new RuntimeEventListItemViewModel(runtimeEvent));
                }

                RuntimeEventLogMessage =
                    F("format.loaded_runtime_events", RuntimeEventLogEntries.Count);
                return;
            }

            RuntimeEventLogMessage = T("logs.runtime_refresh_failed");
            RuntimeEventLogErrorMessage = DescribeError(response);
        }
        finally
        {
            if (requestVersion == runtimeEventLogLoadVersion)
            {
                IsLoadingRuntimeEventLog = false;
            }
        }
    }

    [RelayCommand(CanExecute = nameof(CanRefreshAuditEvents), AllowConcurrentExecutions = true)]
    private async Task RefreshAuditEventsAsync()
    {
        var requestVersion = ++auditEventLogLoadVersion;
        IsLoadingAuditEventLog = true;
        AuditEventLogMessage = T("logs.loading_audit_events");
        AuditEventLogErrorMessage = null;

        try
        {
            var response = await _apiClient.ListAuditEventsAsync(
                BuildSettings(),
                NormalizeFilter(LogWorkflowRunIdFilter),
                NormalizeFilter(LogNodeRunIdFilter),
                NormalizeFilter(LogEventTypeFilter),
                _shutdown.Token);

            if (requestVersion != auditEventLogLoadVersion)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                AuditEvents.Clear();
                foreach (var auditEvent in response.Data)
                {
                    AuditEvents.Add(new AuditEventListItemViewModel(auditEvent));
                }

                AuditEventLogMessage = F("format.loaded_audit_events", AuditEvents.Count);
                return;
            }

            AuditEventLogMessage = T("logs.audit_refresh_failed");
            AuditEventLogErrorMessage = DescribeError(response);
        }
        finally
        {
            if (requestVersion == auditEventLogLoadVersion)
            {
                IsLoadingAuditEventLog = false;
            }
        }
    }

    [RelayCommand(CanExecute = nameof(CanRefreshTableRefs))]
    private async Task RefreshTableRefsAsync()
    {
        if (SelectedRun is null)
        {
            return;
        }

        var requestedRunId = SelectedRun.WorkflowRunId;
        var requestVersion = ++tableRefsLoadVersion;
        IsLoadingTableRefs = true;
        TableRefMessage = F("format.loading_table_refs_for", requestedRunId);
        TableRefErrorMessage = null;

        try
        {
            var response = await _apiClient.ListTableRefsAsync(
                BuildSettings(),
                requestedRunId,
                _shutdown.Token);

            if (
                SelectedRun?.WorkflowRunId != requestedRunId
                || requestVersion != tableRefsLoadVersion)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                TableRefs.Clear();
                foreach (var tableRef in response.Data)
                {
                    TableRefs.Add(new TableRefListItemViewModel(tableRef));
                }

                TableRefMessage = F("format.loaded_table_refs", TableRefs.Count);
                return;
            }

            TableRefMessage = T("data.table_ref_refresh_failed");
            TableRefErrorMessage = DescribeError(response);
        }
        finally
        {
            if (requestVersion == tableRefsLoadVersion)
            {
                IsLoadingTableRefs = false;
            }
        }
    }

    [RelayCommand(CanExecute = nameof(CanRefreshSelectedWorkflowNodeDataPreview))]
    private async Task RefreshSelectedWorkflowNodeDataPreviewAsync()
    {
        await TryRefreshSelectedWorkflowNodeDataPreviewAsync();
    }

    private async Task<bool> TryRefreshSelectedWorkflowNodeDataPreviewAsync()
    {
        if (SelectedRun is null || SelectedWorkflowDefinitionNode is null)
        {
            return false;
        }

        var requestedRunId = SelectedRun.WorkflowRunId;
        var requestedNodeInstanceId = SelectedWorkflowDefinitionNode.NodeInstanceId;
        var requestVersion = ++dataPreviewLoadVersion;
        IsLoadingDataPreview = true;
        DataPreviewMessage = F("format.loading_data_preview", requestedNodeInstanceId);
        DataPreviewErrorMessage = null;

        try
        {
            var nodeRunsResponse = await _apiClient.ListNodeRunsAsync(
                BuildSettings(),
                requestedRunId,
                _shutdown.Token);

            if (IsStaleDataPreviewRequest(requestVersion, requestedRunId, requestedNodeInstanceId))
            {
                return false;
            }

            if (!nodeRunsResponse.Ok || nodeRunsResponse.Data is null)
            {
                DataPreviewMessage = T("data_preview.refresh_failed");
                DataPreviewErrorMessage = DescribeError(nodeRunsResponse);
                return false;
            }

            var nodeRun = nodeRunsResponse.Data.FirstOrDefault(item =>
                string.Equals(
                    item.NodeInstanceId,
                    requestedNodeInstanceId,
                    StringComparison.Ordinal));
            if (nodeRun is null)
            {
                DataPreviewMessage =
                    F("format.data_preview_node_run_not_found", requestedNodeInstanceId);
                return false;
            }

            var tableRefsResponse = await _apiClient.ListTableRefsAsync(
                BuildSettings(),
                requestedRunId,
                _shutdown.Token);

            if (IsStaleDataPreviewRequest(requestVersion, requestedRunId, requestedNodeInstanceId))
            {
                return false;
            }

            if (!tableRefsResponse.Ok || tableRefsResponse.Data is null)
            {
                DataPreviewMessage = T("data_preview.refresh_failed");
                DataPreviewErrorMessage = DescribeError(tableRefsResponse);
                return false;
            }

            var tableRef = tableRefsResponse.Data
                .Where(item =>
                    string.Equals(item.NodeRunId, nodeRun.NodeRunId, StringComparison.Ordinal)
                    && IsReadablePublishedTableRef(item))
                .OrderByDescending(item => item.Version)
                .ThenByDescending(item => item.CreatedAt)
                .FirstOrDefault();
            if (tableRef is null)
            {
                DataPreviewMessage =
                    F("format.data_preview_table_ref_not_found", requestedNodeInstanceId);
                return false;
            }

            var rowsResponse = await _apiClient.GetTableDataRowsAsync(
                BuildSettings(),
                tableRef.TableRefId,
                offset: 0,
                limit: DataPreviewRowLimit,
                cancellationToken: _shutdown.Token);

            if (IsStaleDataPreviewRequest(requestVersion, requestedRunId, requestedNodeInstanceId))
            {
                return false;
            }

            if (!rowsResponse.Ok || rowsResponse.Data is null)
            {
                DataPreviewMessage = T("data_preview.refresh_failed");
                DataPreviewErrorMessage = DescribeError(rowsResponse);
                return false;
            }

            LoadDataPreviewRows(rowsResponse.Data);
            DataPreviewMessage = F(
                "format.loaded_data_preview",
                rowsResponse.Data.Rows.Length,
                rowsResponse.Data.RowCount,
                tableRef.LogicalTableId);
            return true;
        }
        finally
        {
            if (requestVersion == dataPreviewLoadVersion)
            {
                IsLoadingDataPreview = false;
            }
        }
    }

    private async Task RefreshSelectedWorkflowNodeDataPreviewAfterRunStartAsync(
        string workflowRunId)
    {
        for (var attempt = 0; attempt < DataPreviewRunRefreshAttemptCount; attempt++)
        {
            await LoadRunsAsync(workflowRunId);
            var loadedCurrentPreview = false;
            if (CanRefreshSelectedWorkflowNodeDataPreview())
            {
                loadedCurrentPreview = await TryRefreshSelectedWorkflowNodeDataPreviewAsync();
            }

            if (loadedCurrentPreview)
            {
                return;
            }

            if (SelectedRun is not null && IsTerminalRunStatus(SelectedRun.Status))
            {
                return;
            }

            if (attempt + 1 < DataPreviewRunRefreshAttemptCount)
            {
                await _dataPreviewRunRefreshDelay(_shutdown.Token);
            }
        }
    }

    private async Task TrackWorkflowRunUntilTerminalAsync(string workflowRunId)
    {
        for (var attempt = 0; attempt < WorkflowRunTerminalRefreshAttemptCount; attempt++)
        {
            await LoadRunsAsync(workflowRunId);
            if (SelectedRun is not null && IsTerminalRunStatus(SelectedRun.Status))
            {
                return;
            }

            if (attempt + 1 < WorkflowRunTerminalRefreshAttemptCount)
            {
                await _dataPreviewRunRefreshDelay(_shutdown.Token);
            }
        }
    }

    private async Task SelectLatestReadableOutputNodeForRunAsync(string workflowRunId)
    {
        var nodeRunsResponse = await _apiClient.ListNodeRunsAsync(
            BuildSettings(),
            workflowRunId,
            _shutdown.Token);
        if (!nodeRunsResponse.Ok || nodeRunsResponse.Data is null)
        {
            return;
        }

        var tableRefsResponse = await _apiClient.ListTableRefsAsync(
            BuildSettings(),
            workflowRunId,
            _shutdown.Token);
        if (!tableRefsResponse.Ok || tableRefsResponse.Data is null)
        {
            return;
        }

        var nodeInstanceIdsWithReadableOutput = tableRefsResponse.Data
            .Where(IsReadablePublishedTableRef)
            .Join(
                nodeRunsResponse.Data,
                tableRef => tableRef.NodeRunId,
                nodeRun => nodeRun.NodeRunId,
                (_, nodeRun) => nodeRun.NodeInstanceId)
            .ToHashSet(StringComparer.Ordinal);
        var latestOutputNode = WorkflowDefinitionDraftNodes
            .Reverse()
            .FirstOrDefault(node => nodeInstanceIdsWithReadableOutput.Contains(node.NodeInstanceId));
        if (latestOutputNode is not null)
        {
            SelectedWorkflowDefinitionNode = latestOutputNode;
        }
    }

    private bool IsStaleDataPreviewRequest(
        int requestVersion,
        string requestedRunId,
        string requestedNodeInstanceId)
    {
        return requestVersion != dataPreviewLoadVersion
            || !string.Equals(
                SelectedRun?.WorkflowRunId,
                requestedRunId,
                StringComparison.Ordinal)
            || !string.Equals(
                SelectedWorkflowDefinitionNode?.NodeInstanceId,
                requestedNodeInstanceId,
                StringComparison.Ordinal);
    }

    private static bool IsReadablePublishedTableRef(TableRefDto tableRef)
    {
        return string.Equals(
                tableRef.LifecycleStatus,
                "PUBLISHED",
                StringComparison.OrdinalIgnoreCase)
            && tableRef.Capabilities.Any(capability =>
                string.Equals(capability, "READ", StringComparison.OrdinalIgnoreCase));
    }

    private void ResetDataPreviewSelectionState()
    {
        dataPreviewLoadVersion++;
        IsLoadingDataPreview = false;
        DataPreviewMessage = T("status.select_run_and_workflow_node_data_preview");
        DataPreviewErrorMessage = null;
        RefreshSelectedWorkflowNodeDataPreviewCommand.NotifyCanExecuteChanged();
    }

    private void LoadDataPreviewRows(TableDataRowsDto rows)
    {
        DataPreviewColumns.Clear();
        foreach (var column in rows.Columns)
        {
            DataPreviewColumns.Add(new TableDataPreviewColumnViewModel(column));
        }

        DataPreviewRows.Clear();
        foreach (var row in rows.Rows)
        {
            DataPreviewRows.Add(
                new TableDataPreviewRowViewModel(
                    rows.Columns
                        .Select(
                            column =>
                                new TableDataPreviewCellViewModel(
                                    FormatDataPreviewCell(row, column)))
                        .ToArray()));
        }

        NotifyDataPreviewRowsChanged();
    }

    private void NotifyDataPreviewRowsChanged()
    {
        OnPropertyChanged(nameof(HasDataPreviewColumns));
        OnPropertyChanged(nameof(HasDataPreviewRows));
    }

    private static string FormatDataPreviewCell(JsonElement row, string column)
    {
        if (row.ValueKind != JsonValueKind.Object
            || !row.TryGetProperty(column, out var value))
        {
            return string.Empty;
        }

        return value.ValueKind switch
        {
            JsonValueKind.Null or JsonValueKind.Undefined => string.Empty,
            JsonValueKind.String => value.GetString() ?? string.Empty,
            JsonValueKind.Number or JsonValueKind.True or JsonValueKind.False =>
                value.GetRawText(),
            _ => value.GetRawText(),
        };
    }

    [RelayCommand(CanExecute = nameof(CanRefreshSharedPublications))]
    private async Task RefreshSharedPublicationsAsync()
    {
        if (!TryParseLimit(
            SharedPublicationLimitFilter,
            T("data.shared_publication_limit_label"),
            out var limit,
            out var error))
        {
            SharedPublicationMessage = T("data.shared_publication_refresh_rejected");
            SharedPublicationErrorMessage = error;
            return;
        }

        var requestVersion = ++sharedPublicationsLoadVersion;
        IsLoadingSharedPublications = true;
        SharedPublicationMessage = T("data.loading_shared_publications");
        SharedPublicationErrorMessage = null;

        try
        {
            var response = await _apiClient.ListSharedPublicationsAsync(
                BuildSettings(),
                NormalizeFilter(SharedPublicationShareNameFilter),
                limit,
                _shutdown.Token);

            if (requestVersion != sharedPublicationsLoadVersion)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                var previousPublicationId = SelectedSharedPublication?.PublicationId;
                SharedPublications.Clear();
                foreach (var publication in response.Data)
                {
                    SharedPublications.Add(
                        new SharedPublicationListItemViewModel(publication, DisplayTextFormatter));
                }

                SelectedSharedPublication = SharedPublications.FirstOrDefault(
                    publication => publication.PublicationId == previousPublicationId)
                    ?? SharedPublications.FirstOrDefault();
                SharedPublicationMessage =
                    F("format.loaded_shared_publications", SharedPublications.Count);
                return;
            }

            SharedPublicationMessage = T("data.shared_publication_refresh_failed");
            SharedPublicationErrorMessage = DescribeError(response);
        }
        finally
        {
            if (requestVersion == sharedPublicationsLoadVersion)
            {
                IsLoadingSharedPublications = false;
            }
        }
    }

    [RelayCommand(CanExecute = nameof(CanRefreshSharedPublicationVersions))]
    private async Task RefreshSharedPublicationVersionsAsync()
    {
        var shareName = NormalizeFilter(SharedPublicationVersionShareNameFilter)
            ?? SelectedSharedPublication?.ShareName;
        if (string.IsNullOrWhiteSpace(shareName))
        {
            SharedPublicationVersionMessage = T("data.shared_publication_versions_rejected");
            SharedPublicationVersionErrorMessage =
                T("data.share_name_required_for_versions");
            return;
        }

        if (!TryParseLimit(
            SharedPublicationVersionLimitFilter,
            T("data.shared_publication_version_limit_label"),
            out var limit,
            out var error))
        {
            SharedPublicationVersionMessage = T("data.shared_publication_versions_rejected");
            SharedPublicationVersionErrorMessage = error;
            return;
        }

        var requestVersion = ++sharedPublicationVersionsLoadVersion;
        IsLoadingSharedPublicationVersions = true;
        SharedPublicationVersionMessage = F("format.loading_versions_for", shareName);
        SharedPublicationVersionErrorMessage = null;

        try
        {
            var response = await _apiClient.ListSharedPublicationVersionsAsync(
                BuildSettings(),
                shareName,
                limit,
                _shutdown.Token);

            if (requestVersion != sharedPublicationVersionsLoadVersion)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                SharedPublicationVersions.Clear();
                foreach (var publication in response.Data)
                {
                    SharedPublicationVersions.Add(
                        new SharedPublicationListItemViewModel(publication, DisplayTextFormatter));
                }

                SharedPublicationVersionMessage =
                    F(
                        "format.loaded_shared_publication_versions",
                        SharedPublicationVersions.Count,
                        shareName);
                return;
            }

            SharedPublicationVersionMessage = T("data.shared_publication_versions_refresh_failed");
            SharedPublicationVersionErrorMessage = DescribeError(response);
        }
        finally
        {
            if (requestVersion == sharedPublicationVersionsLoadVersion)
            {
                IsLoadingSharedPublicationVersions = false;
            }
        }
    }

    private async Task LoadNodeRunsForSelectedRunAsync()
    {
        if (SelectedRun is null)
        {
            return;
        }

        var requestedRunId = SelectedRun.WorkflowRunId;
        var requestVersion = ++nodeRunsLoadVersion;
        IsLoadingNodeRuns = true;
        NodeRunMessage = F("format.loading_nodes_for", requestedRunId);
        NodeRunErrorMessage = null;

        try
        {
            var response = await _apiClient.ListNodeRunsAsync(
                BuildSettings(),
                requestedRunId,
                _shutdown.Token);

            if (
                SelectedRun?.WorkflowRunId != requestedRunId
                || requestVersion != nodeRunsLoadVersion)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                NodeRuns.Clear();
                foreach (var nodeRun in response.Data)
                {
                    NodeRuns.Add(new NodeRunListItemViewModel(nodeRun, DisplayTextFormatter));
                }

                NodeRunMessage = F("format.loaded_node_runs", NodeRuns.Count);
                return;
            }

            NodeRunMessage = T("node_runs.refresh_failed");
            NodeRunErrorMessage = DescribeError(response);
        }
        finally
        {
            if (requestVersion == nodeRunsLoadVersion)
            {
                IsLoadingNodeRuns = false;
            }
        }
    }

    private async Task RunRuntimeEventStreamLoopAsync(CancellationToken cancellationToken)
    {
        try
        {
            while (!cancellationToken.IsCancellationRequested)
            {
                try
                {
                    RuntimeEventStreamMessage = T("events.stream_connecting");
                    RuntimeEventStreamErrorMessage = null;

                    await using var stream = await _runtimeEventStreamClient.ConnectAsync(
                        BuildSettings(),
                        cancellationToken);
                    IsRuntimeEventStreamConnected = true;
                    RuntimeEventStreamMessage = T("events.stream_connected");
                    await RecoverRuntimeStateAsync(cancellationToken: cancellationToken);

                    while (!cancellationToken.IsCancellationRequested)
                    {
                        var runtimeEvent = await stream.ReadNextAsync(cancellationToken);
                        if (runtimeEvent is null)
                        {
                            IsRuntimeEventStreamConnected = false;
                            RuntimeEventStreamMessage =
                                T("events.stream_disconnected_reconnecting");
                            await RecoverRuntimeStateAsync(cancellationToken: cancellationToken);
                            break;
                        }

                        await AcceptRuntimeEventAsync(runtimeEvent, cancellationToken);
                    }
                }
                catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
                {
                    break;
                }
                catch (Exception ex)
                {
                    IsRuntimeEventStreamConnected = false;
                    RuntimeEventStreamMessage = T("events.stream_error_reconnecting");
                    RuntimeEventStreamErrorMessage =
                        F(
                            "format.events.stream_connection_failed",
                            EngineHostConnectionDiagnostics.RedactToken(ex.Message));
                    await RecoverRuntimeStateAsync(cancellationToken: cancellationToken);
                }

                if (!cancellationToken.IsCancellationRequested)
                {
                    await _runtimeEventReconnectDelay(cancellationToken);
                }
            }
        }
        finally
        {
            IsRuntimeEventStreamConnected = false;
            IsRuntimeEventStreamRunning = false;
            if (_runtimeEventStreamCancellation?.Token == cancellationToken)
            {
                _runtimeEventStreamCancellation.Dispose();
                _runtimeEventStreamCancellation = null;
                _runtimeEventStreamTask = null;
            }
        }
    }

    private async Task AcceptRuntimeEventAsync(
        RuntimeEventDto runtimeEvent,
        CancellationToken cancellationToken)
    {
        RuntimeEvents.Insert(0, new RuntimeEventListItemViewModel(runtimeEvent));
        while (RuntimeEvents.Count > MaxRuntimeEvents)
        {
            RuntimeEvents.RemoveAt(RuntimeEvents.Count - 1);
        }

        OnPropertyChanged(nameof(HasRuntimeEvents));
        LastRuntimeEventSequenceNumber = runtimeEvent.SequenceNumber;
        RuntimeEventStreamMessage =
            F(
                "format.received_runtime_event",
                runtimeEvent.EventType,
                runtimeEvent.SequenceNumber);
        RuntimeEventStreamErrorMessage = null;

        await RecoverRuntimeStateAsync(
            runtimeEvent.WorkflowRunId,
            cancellationToken);
    }

    private async Task RecoverRuntimeStateAsync(
        string? selectWorkflowRunId = null,
        CancellationToken cancellationToken = default)
    {
        try
        {
            await LoadRunsAsync(selectWorkflowRunId);
            if (SelectedRun is not null)
            {
                await LoadNodeRunsForSelectedRunAsync();
            }
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception ex)
        {
            RuntimeEventStreamErrorMessage = ex.Message;
        }
    }

    private async Task LoadRunsAsync(string? selectWorkflowRunId = null)
    {
        IsLoadingRuns = true;
        RunMessage = SelectedWorkflow is null
            ? T("runs.loading")
            : F("format.loading_runs_for", SelectedWorkflow.Name);
        RunErrorMessage = null;

        var workflowId = SelectedWorkflow?.WorkflowId;
        var response = await _apiClient.ListRunsAsync(
            BuildSettings(),
            workflowId,
            cancellationToken: _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            var previousRunId = selectWorkflowRunId ?? SelectedRun?.WorkflowRunId;
            Runs.Clear();
            foreach (var run in response.Data)
            {
                Runs.Add(new WorkflowRunListItemViewModel(run));
            }

            SelectedRun = Runs.FirstOrDefault(run => run.WorkflowRunId == previousRunId)
                ?? Runs.FirstOrDefault();
            RunMessage = workflowId is null
                ? F("format.loaded_runs", Runs.Count)
                : F("format.loaded_runs_for", Runs.Count, SelectedWorkflow?.Name);
            IsLoadingRuns = false;
            return;
        }

        RunMessage = T("runs.refresh_failed");
        RunErrorMessage = DescribeError(response);
        IsLoadingRuns = false;
    }

    private async Task RefreshWorkflowsSelectingAsync(string workflowId)
    {
        IsLoadingWorkflows = true;
        WorkflowMessage = T("workflow.refreshing");
        WorkflowErrorMessage = null;

        var response = await _apiClient.ListWorkflowsAsync(
            BuildSettings(),
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            Workflows.Clear();
            foreach (var workflow in response.Data)
            {
                Workflows.Add(new WorkflowListItemViewModel(workflow));
            }

            SelectedWorkflow = Workflows.FirstOrDefault(workflow => workflow.WorkflowId == workflowId)
                ?? Workflows.FirstOrDefault();
            WorkflowMessage = F("format.loaded_workflows", Workflows.Count);
            IsLoadingWorkflows = false;
            return;
        }

        WorkflowMessage = T("workflow.refresh_failed");
        WorkflowErrorMessage = DescribeError(response);
        IsLoadingWorkflows = false;
    }

    private EngineHostConnectionSettings BuildSettings()
    {
        return new EngineHostConnectionSettings
        {
            BaseUrl = BaseUrl,
            Token = Token,
        };
    }

    private async Task SaveConnectionSettingsAsync(
        EngineHostConnectionSettings settings)
    {
        try
        {
            await _connectionSettingsStore.SaveAsync(
                PersistedConnectionSettings.FromBaseUrl(
                    settings.BaseUrl,
                    settings.Token,
                    runtimeEventStreamAutoConnect: runtimeEventStreamAutoConnect),
                _shutdown.Token);
        }
        catch (OperationCanceledException) when (_shutdown.Token.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception ex)
        {
            ErrorMessage = F("format.connection_settings_save_failed", ex.Message);
        }
    }

    private string DescribeError<TData>(ApiResponseEnvelope<TData> response)
    {
        if (response.Error is null)
        {
            return T("diagnostics.response_missing_data");
        }

        if (response.Error.ErrorCode is "TOKEN_REQUIRED" or "UNAUTHORIZED")
        {
            IsAuthenticationFailed = true;
        }

        return response.Error.ErrorCode switch
        {
            "TOKEN_REQUIRED" => T("diagnostics.token_required"),
            "UNAUTHORIZED" => T("diagnostics.token_invalid"),
            "INVALID_BASE_URL" => F(
                "format.diagnostics.invalid_base_url",
                response.Error.Message),
            "REQUEST_TIMEOUT" => T("diagnostics.request_timeout"),
            "REQUEST_FAILED" => F(
                "format.diagnostics.request_failed",
                response.Error.Message),
            _ => $"{response.Error.ErrorCode}: {response.Error.Message}",
        };
    }

    private string LocalizeHealthStatusMessage(EngineHostHealthCheckResult result)
    {
        if (result.IsHealthy)
        {
            return T("connection.health_check_passed");
        }

        return string.Equals(result.Message, "Connection failed.", StringComparison.Ordinal)
            ? T("connection.failed")
            : result.Message;
    }

    private string? LocalizeHealthErrorMessage(string? message)
    {
        return message switch
        {
            null => null,
            "Connection timed out." => T("connection.timed_out"),
            "EngineHost health response was not recognized." =>
                T("connection.health_response_unrecognized"),
            "EngineHost base URL is required." => T("connection.base_url_required"),
            "EngineHost base URL must be an absolute URL." => T("connection.base_url_absolute"),
            "EngineHost base URL must use HTTP or HTTPS." => T("connection.base_url_http_https"),
            _ => message,
        };
    }

    private static string? FormatValidationIssues(WorkflowValidationResultDto result)
    {
        var issueLines = result.Errors
            .Concat(result.Warnings)
            .Select(issue =>
                string.IsNullOrWhiteSpace(issue.Path)
                    ? $"{issue.Code}: {issue.Message}"
                    : $"{issue.Code} at {issue.Path}: {issue.Message}")
            .ToArray();

        return issueLines.Length == 0
            ? null
            : string.Join(Environment.NewLine, issueLines);
    }

    private static string? FormatNodeConfigApplyErrors(
        NodeConfigEditableDraftConfigResult result)
    {
        var fieldWarningCodes = result.FieldErrors
            .Select(error => error.Warning)
            .ToHashSet(StringComparer.Ordinal);
        var issueLines = result.FieldErrors
            .Select(error => $"{error.FieldName}: {error.Warning}")
            .Concat(result.Warnings.Where(warning => !fieldWarningCodes.Contains(warning)))
            .Where(line => !string.IsNullOrWhiteSpace(line))
            .ToArray();

        return issueLines.Length == 0
            ? null
            : string.Join(Environment.NewLine, issueLines);
    }

    private NodeDefinitionListItemViewModel? FindNodeDefinition(
        WorkflowDefinitionNodeListItemViewModel node)
    {
        return NodeDefinitions.FirstOrDefault(definition =>
            string.Equals(definition.NodeType, node.NodeType, StringComparison.Ordinal)
            && string.Equals(
                definition.NodeVersion,
                node.NodeVersion,
                StringComparison.Ordinal));
    }

    private void RefreshWorkflowDefinitionDraftStructureState()
    {
        WorkflowDefinitionDraftStructure = string.IsNullOrWhiteSpace(
            WorkflowDefinitionDraftJson)
            ? null
            : WorkflowDefinitionDraftStructureBuilder.Build(
                WorkflowDefinitionDraftJson,
                DisplayTextFormatter);
        RefreshWorkflowDefinitionDraftNodes();
        ClearSelectedWorkflowDefinitionDraftNodeIfMissing();
        ClearSelectedWorkflowDefinitionDraftConnectionIfMissing();
        ClearSelectedNewDraftConnectionNodesIfMissing();
    }

    private void RefreshWorkflowDefinitionDraftNodes()
    {
        var selectedNodeId = SelectedWorkflowDefinitionNode?.NodeInstanceId;
        var hadSelectedNode = !string.IsNullOrWhiteSpace(selectedNodeId);
        var batchSelectedNodeIds = WorkflowDefinitionDraftNodes
            .Where(node => node.IsBatchSelected)
            .Select(node => node.NodeInstanceId)
            .ToHashSet(StringComparer.Ordinal);

        foreach (var node in WorkflowDefinitionDraftNodes)
        {
            node.PropertyChanged -= OnWorkflowDefinitionDraftNodeItemPropertyChanged;
        }

        WorkflowDefinitionDraftNodes.Clear();

        if (WorkflowDefinitionDraftStructure is not null)
        {
            foreach (var node in WorkflowDefinitionDraftStructure.Nodes)
            {
                var nodeItem = new WorkflowDefinitionNodeListItemViewModel(
                    node.NodeInstanceId,
                    node.NodeType,
                    node.NodeVersion,
                    node.DisplayName,
                    node.Enabled,
                    node.ConfigJson,
                    DisplayTextFormatter,
                    _nodeEditorResolver.Resolve(node.NodeType, node.DisplayName))
                {
                    IsBatchSelected = batchSelectedNodeIds.Contains(node.NodeInstanceId),
                };
                nodeItem.PropertyChanged += OnWorkflowDefinitionDraftNodeItemPropertyChanged;
                WorkflowDefinitionDraftNodes.Add(nodeItem);
            }
        }

        SelectedWorkflowDefinitionNode = WorkflowDefinitionDraftNodes.FirstOrDefault(node =>
            string.Equals(node.NodeInstanceId, selectedNodeId, StringComparison.Ordinal));
        if (SelectedWorkflowDefinitionNode is null && !hadSelectedNode)
        {
            SelectedWorkflowDefinitionNode = WorkflowDefinitionDraftNodes.FirstOrDefault();
        }

        OnPropertyChanged(nameof(WorkflowDefinitionDraftNodeCountText));
        RefreshWorkflowDefinitionBatchSelectionState();
    }

    private void SelectWorkflowDefinitionDraftNode(string nodeInstanceId)
    {
        SelectedWorkflowDefinitionNode = WorkflowDefinitionDraftNodes.FirstOrDefault(node =>
            string.Equals(
                node.NodeInstanceId,
                nodeInstanceId,
                StringComparison.Ordinal));
    }

    private void ResetNewDraftNodeInput()
    {
        lastSuggestedNewDraftNodeInstanceId = string.Empty;
        lastSuggestedNewDraftNodeConfigJson = "{}";
        SelectedNewDraftNodeDefinition = null;
        NewDraftNodeInstanceId = string.Empty;
        NewDraftNodeType = string.Empty;
        NewDraftNodeVersion = "1.0";
        NewDraftNodeDisplayName = string.Empty;
        NewDraftNodeConfigJson = "{}";
    }

    private void ResetWorkflowDefinitionDraftSelectionInput()
    {
        SelectedWorkflowDefinitionDraftNodeInstanceId = string.Empty;
        SelectedWorkflowDefinitionDraftConnectionId = string.Empty;
    }

    private void ClearWorkflowDefinitionDraftBatchSelection()
    {
        foreach (var node in WorkflowDefinitionDraftNodes)
        {
            node.IsBatchSelected = false;
        }

        RefreshWorkflowDefinitionBatchSelectionState();
    }

    private void OnWorkflowDefinitionDraftNodeItemPropertyChanged(
        object? sender,
        PropertyChangedEventArgs args)
    {
        if (args.PropertyName == nameof(WorkflowDefinitionNodeListItemViewModel.IsBatchSelected))
        {
            RefreshWorkflowDefinitionBatchSelectionState();
        }
    }

    private void RefreshWorkflowDefinitionBatchSelectionState()
    {
        OnPropertyChanged(nameof(WorkflowDefinitionBatchSelectedNodeCount));
        OnPropertyChanged(nameof(WorkflowDefinitionBatchSelectedNodeCountText));
        DeleteSelectedWorkflowDefinitionDraftNodesCommand.NotifyCanExecuteChanged();
    }

    private void ResetNewDraftConnectionInput()
    {
        lastSuggestedNewDraftConnectionId = string.Empty;
        SelectedNewDraftConnectionSourceNode = null;
        SelectedNewDraftConnectionTargetNode = null;
        NewDraftConnectionId = string.Empty;
        NewDraftConnectionSourceNodeId = string.Empty;
        NewDraftConnectionSourcePort = string.Empty;
        NewDraftConnectionTargetNodeId = string.Empty;
        NewDraftConnectionTargetPort = string.Empty;
    }

    private void ClearSelectedWorkflowDefinitionDraftNodeIfMissing()
    {
        if (string.IsNullOrWhiteSpace(SelectedWorkflowDefinitionDraftNodeInstanceId))
        {
            return;
        }

        if (WorkflowDefinitionDraftStructure?.Nodes.Any(node =>
            string.Equals(
                node.NodeInstanceId,
                SelectedWorkflowDefinitionDraftNodeInstanceId,
                StringComparison.Ordinal)) == true)
        {
            return;
        }

        SelectedWorkflowDefinitionDraftNodeInstanceId = string.Empty;
    }

    private void ClearSelectedWorkflowDefinitionDraftConnectionIfMissing()
    {
        if (string.IsNullOrWhiteSpace(SelectedWorkflowDefinitionDraftConnectionId))
        {
            return;
        }

        if (WorkflowDefinitionDraftStructure?.Connections.Any(connection =>
            string.Equals(
                connection.ConnectionId,
                SelectedWorkflowDefinitionDraftConnectionId,
                StringComparison.Ordinal)) == true)
        {
            return;
        }

        SelectedWorkflowDefinitionDraftConnectionId = string.Empty;
    }

    private void ClearSelectedNewDraftConnectionNodesIfMissing()
    {
        if (SelectedNewDraftConnectionSourceNode is not null)
        {
            SelectedNewDraftConnectionSourceNode = FindDraftNode(
                SelectedNewDraftConnectionSourceNode.NodeInstanceId);
        }

        if (SelectedNewDraftConnectionTargetNode is not null)
        {
            SelectedNewDraftConnectionTargetNode = FindDraftNode(
                SelectedNewDraftConnectionTargetNode.NodeInstanceId);
        }
    }

    private WorkflowDefinitionDraftNode? FindDraftNode(string nodeInstanceId)
    {
        return WorkflowDefinitionDraftStructure?.Nodes.FirstOrDefault(node =>
            string.Equals(
                node.NodeInstanceId,
                nodeInstanceId,
                StringComparison.Ordinal));
    }

    private void ResetWorkflowDefinitionStructuredEditInput()
    {
        IsWorkflowAddNodePanelVisible = false;
        lastSuggestedNewDraftNodeInstanceId = string.Empty;
        lastSuggestedNewDraftConnectionId = string.Empty;
        ResetNewDraftNodeInput();
        ResetNewDraftConnectionInput();
        ResetWorkflowDefinitionDraftSelectionInput();
    }

    private void RefreshSelectedNodeDisplayNameDraftState()
    {
        SelectedNodeDisplayNameDraft = SelectedWorkflowDefinitionNode?.DisplayName ?? string.Empty;
    }

    private void RefreshSelectedNodeConfigDraftState()
    {
        if (WorkflowDefinitionDetail is null ||
            SelectedWorkflowDefinitionNode is null)
        {
            SelectedNodeConfigDraft = null;
            SelectedNodeConfigEditableDraft = null;
            RebuildSelectedNodeConfigEditableInputFields(null);
            SelectedNodeConfigEditableDraftMessage =
                DisplayTextFormatter.FormatSelectedNodeConfigDraftMissingSelection();
            OnPropertyChanged(nameof(SelectedNodeConfigDraftSummaryText));
            return;
        }

        var schema = FindNodeDefinition(SelectedWorkflowDefinitionNode)
            ?.ConfigSchemaDescriptor;
        var draft = NodeConfigDraftBuilder.Build(
            WorkflowDefinitionDraftJson,
            SelectedWorkflowDefinitionNode.NodeInstanceId,
            schema);

        SelectedNodeConfigDraft = draft;
        if (!draft.IsSupported)
        {
            SelectedNodeConfigEditableDraft = null;
            RebuildSelectedNodeConfigEditableInputFields(null);
            SelectedNodeConfigEditableDraftMessage =
                DisplayTextFormatter.FormatSelectedNodeConfigDraftSchemaUnavailable();
            OnPropertyChanged(nameof(SelectedNodeConfigDraftSummaryText));
            return;
        }

        var editableDraft = NodeConfigEditableDraftBuilder.Build(draft);
        SelectedNodeConfigEditableDraft = editableDraft;
        RebuildSelectedNodeConfigEditableInputFields(editableDraft);
        SelectedNodeConfigEditableDraftMessage =
            DisplayTextFormatter.FormatSelectedNodeConfigDraftReady(
                SelectedWorkflowDefinitionNode.NodeInstanceId,
                draft.Fields.Count(item => item.IsEditable),
                draft.Fields.Count(item => !item.IsEditable));
        OnPropertyChanged(nameof(SelectedNodeConfigDraftSummaryText));
    }

    private void RebuildSelectedNodeConfigEditableInputFields(
        NodeConfigEditableDraft? editableDraft)
    {
        SelectedNodeConfigEditableInputFields.Clear();
        if (editableDraft is not null)
        {
            var nodeType = SelectedWorkflowDefinitionNode?.NodeType ?? string.Empty;
            foreach (var field in editableDraft.Fields)
            {
                SelectedNodeConfigEditableInputFields.Add(
                    new NodeConfigEditableFieldInputViewModel(
                        field,
                        nodeType,
                        DisplayTextFormatter));
            }
        }

        OnPropertyChanged(nameof(HasSelectedNodeConfigEditableInputFields));
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
    }

    private bool TryParseRuntimeEventLogFilters(
        out long? afterSequenceNumber,
        out int limit,
        out string? error)
    {
        afterSequenceNumber = null;
        limit = 100;
        error = null;

        var afterSequenceNumberText = NormalizeFilter(RuntimeEventAfterSequenceNumberFilter);
        if (afterSequenceNumberText is not null)
        {
            if (!long.TryParse(afterSequenceNumberText, out var parsedAfterSequenceNumber)
                || parsedAfterSequenceNumber < 0)
            {
                error = T("logs.after_sequence_invalid");
                return false;
            }

            afterSequenceNumber = parsedAfterSequenceNumber;
        }

        var limitText = NormalizeFilter(RuntimeEventLimitFilter);
        if (limitText is null)
        {
            return true;
        }

        if (!int.TryParse(limitText, out var parsedLimit)
            || parsedLimit is < 1 or > 1000)
        {
            error = T("logs.runtime_event_limit_invalid");
            return false;
        }

        limit = parsedLimit;
        return true;
    }

    private string BuildLimitRangeError(string label)
    {
        return F("format.limit_between", label);
    }

    private bool TryParseLimit(
        string limitFilter,
        string label,
        out int limit,
        out string? error)
    {
        limit = 100;
        error = null;

        var limitText = NormalizeFilter(limitFilter);
        if (limitText is null)
        {
            return true;
        }

        if (!int.TryParse(limitText, out var parsedLimit)
            || parsedLimit is < 1 or > 1000)
        {
            error = BuildLimitRangeError(label);
            return false;
        }

        limit = parsedLimit;
        return true;
    }

    private static string? NormalizeFilter(string value)
    {
        return string.IsNullOrWhiteSpace(value) ? null : value.Trim();
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

    private string? LocalizeWorkflowDefinitionDraftWarning(string? warning)
    {
        if (string.IsNullOrWhiteSpace(warning))
        {
            return warning;
        }

        return warning switch
        {
            "WORKFLOW_DRAFT_JSON_INVALID" => T("definition.warning.workflow_draft_json_invalid"),
            "WORKFLOW_DRAFT_ROOT_NOT_OBJECT" => T("definition.warning.workflow_draft_root_not_object"),
            "WORKFLOW_DRAFT_NODES_MISSING" => T("definition.warning.workflow_draft_nodes_missing"),
            "WORKFLOW_DRAFT_CONNECTIONS_MISSING" => T("definition.warning.workflow_draft_connections_missing"),
            "NODE_INSTANCE_ID_REQUIRED" => T("definition.warning.node_instance_id_required"),
            "NODE_TYPE_REQUIRED" => T("definition.warning.node_type_required"),
            "NODE_VERSION_REQUIRED" => T("definition.warning.node_version_required"),
            "CONFIG_UNSUPPORTED" => T("definition.warning.node_config_unsupported"),
            "NODE_ALREADY_EXISTS" => T("definition.warning.node_already_exists"),
            "NODE_NOT_FOUND" => T("definition.warning.node_not_found"),
            "INSERT_AFTER_NODE_NOT_FOUND" => T("definition.warning.insert_after_node_not_found"),
            "NODE_MOVE_OUT_OF_RANGE" => T("definition.warning.node_move_out_of_range"),
            "NODE_HAS_CONNECTIONS" => T("definition.warning.node_has_connections"),
            "CONNECTION_ID_REQUIRED" => T("definition.warning.connection_id_required"),
            "CONNECTION_ALREADY_EXISTS" => T("definition.warning.connection_already_exists"),
            "CONNECTION_NOT_FOUND" => T("definition.warning.connection_not_found"),
            "SOURCE_NODE_ID_REQUIRED" => T("definition.warning.source_node_id_required"),
            "SOURCE_NODE_NOT_FOUND" => T("definition.warning.source_node_not_found"),
            "SOURCE_PORT_REQUIRED" => T("definition.warning.source_port_required"),
            "TARGET_NODE_ID_REQUIRED" => T("definition.warning.target_node_id_required"),
            "TARGET_NODE_NOT_FOUND" => T("definition.warning.target_node_not_found"),
            "TARGET_PORT_REQUIRED" => T("definition.warning.target_port_required"),
            _ => warning,
        };
    }

    private string? FormatRemovedConnectionsMessage(
        IReadOnlyList<WorkflowDefinitionDraftConnection> removedConnections)
    {
        if (removedConnections.Count == 0)
        {
            return null;
        }

        return F(
            "definition.node_delete_removed_connections",
            string.Join(
                Environment.NewLine,
                removedConnections.Select(FormatRelatedConnectionSummary)));
    }

    private string? FormatAutoWiredConnectionsMessage(
        IReadOnlyList<WorkflowDefinitionDraftConnection> removedConnections,
        IReadOnlyList<WorkflowDefinitionDraftConnection> addedConnections)
    {
        if (removedConnections.Count == 0 && addedConnections.Count == 0)
        {
            return null;
        }

        var removedText = removedConnections.Count == 0
            ? "-"
            : string.Join(
                Environment.NewLine,
                removedConnections.Select(FormatRelatedConnectionSummary));
        var addedText = addedConnections.Count == 0
            ? "-"
            : string.Join(
                Environment.NewLine,
                addedConnections.Select(FormatRelatedConnectionSummary));

        return F(
            "definition.node_add_rewired_connections",
            removedText,
            addedText);
    }

    private static string FormatRelatedConnectionSummary(
        WorkflowDefinitionDraftConnection connection)
    {
        var connectionId = string.IsNullOrWhiteSpace(connection.ConnectionId)
            ? "?"
            : connection.ConnectionId;

        return
            $"- {connectionId}: {FormatConnectionEndpoint(connection.SourceNodeId, connection.SourcePort)} -> {FormatConnectionEndpoint(connection.TargetNodeId, connection.TargetPort)}";
    }

    private static string FormatConnectionEndpoint(string nodeId, string port)
    {
        if (string.IsNullOrWhiteSpace(nodeId))
        {
            return string.IsNullOrWhiteSpace(port) ? "?" : port;
        }

        return string.IsNullOrWhiteSpace(port)
            ? nodeId
            : $"{nodeId}.{port}";
    }

    private void ApplySelectedNewDraftNodeDefinition(
        NodeDefinitionListItemViewModel definition)
    {
        NewDraftNodeType = definition.NodeType;
        NewDraftNodeVersion = string.IsNullOrWhiteSpace(definition.NodeVersion)
            ? "1.0"
            : definition.NodeVersion;

        if (string.IsNullOrWhiteSpace(NewDraftNodeDisplayName))
        {
            NewDraftNodeDisplayName = definition.DisplayNameText;
        }

        if (ShouldApplySuggestedNewDraftNodeInstanceId())
        {
            lastSuggestedNewDraftNodeInstanceId =
                BuildUniqueNewDraftNodeInstanceId(definition.NodeType);
            NewDraftNodeInstanceId = lastSuggestedNewDraftNodeInstanceId;
        }

        if (ShouldApplySuggestedNewDraftNodeConfigJson())
        {
            lastSuggestedNewDraftNodeConfigJson =
                NodeConfigDefaultBuilder.BuildJson(definition.ConfigSchemaDescriptor);
            NewDraftNodeConfigJson = lastSuggestedNewDraftNodeConfigJson;
        }
    }

    private (string? InputPort, string? OutputPort) TryGetAutoWirePorts()
    {
        var definition = SelectedNewDraftNodeDefinition;
        if (definition is null ||
            definition.InputPorts.Length != 1 ||
            definition.OutputPorts.Length != 1)
        {
            return (null, null);
        }

        return (definition.InputPorts[0].Name, definition.OutputPorts[0].Name);
    }

    private bool ShouldApplySuggestedNewDraftNodeInstanceId()
    {
        return string.IsNullOrWhiteSpace(NewDraftNodeInstanceId)
            || string.Equals(
                NewDraftNodeInstanceId,
                lastSuggestedNewDraftNodeInstanceId,
                StringComparison.Ordinal);
    }

    private bool ShouldApplySuggestedNewDraftNodeConfigJson()
    {
        return string.IsNullOrWhiteSpace(NewDraftNodeConfigJson)
            || string.Equals(NewDraftNodeConfigJson.Trim(), "{}", StringComparison.Ordinal)
            || string.Equals(
                NewDraftNodeConfigJson,
                lastSuggestedNewDraftNodeConfigJson,
                StringComparison.Ordinal);
    }

    private string BuildUniqueNewDraftNodeInstanceId(string nodeType)
    {
        var baseId = BuildNewDraftNodeInstanceIdBase(nodeType);
        var existingIds = WorkflowDefinitionDraftStructure?.Nodes
            .Select(node => node.NodeInstanceId)
            .ToHashSet(StringComparer.Ordinal)
            ?? new HashSet<string>(StringComparer.Ordinal);

        var candidate = baseId;
        var suffix = 2;
        while (existingIds.Contains(candidate))
        {
            candidate = $"{baseId}_{suffix}";
            suffix++;
        }

        return candidate;
    }

    private static string BuildNewDraftNodeInstanceIdBase(string nodeType)
    {
        var source = string.IsNullOrWhiteSpace(nodeType)
            ? "node"
            : nodeType.Trim();

        if (source.EndsWith("Node", StringComparison.Ordinal) && source.Length > 4)
        {
            source = source[..^4];
        }

        return BuildSnakeCaseIdentifier(source, "node");
    }

    private void ApplySelectedNewDraftConnectionSourceNode(
        WorkflowDefinitionDraftNode node)
    {
        NewDraftConnectionSourceNodeId = node.NodeInstanceId;
        ApplySuggestedNewDraftConnectionId();
    }

    private void ApplySelectedNewDraftConnectionTargetNode(
        WorkflowDefinitionDraftNode node)
    {
        NewDraftConnectionTargetNodeId = node.NodeInstanceId;
        ApplySuggestedNewDraftConnectionId();
    }

    private void ApplySuggestedNewDraftConnectionId()
    {
        if (string.IsNullOrWhiteSpace(NewDraftConnectionSourceNodeId) ||
            string.IsNullOrWhiteSpace(NewDraftConnectionTargetNodeId) ||
            !ShouldApplySuggestedNewDraftConnectionId())
        {
            return;
        }

        lastSuggestedNewDraftConnectionId = BuildUniqueNewDraftConnectionId(
            NewDraftConnectionSourceNodeId,
            NewDraftConnectionTargetNodeId);
        NewDraftConnectionId = lastSuggestedNewDraftConnectionId;
    }

    private bool ShouldApplySuggestedNewDraftConnectionId()
    {
        return string.IsNullOrWhiteSpace(NewDraftConnectionId)
            || string.Equals(
                NewDraftConnectionId,
                lastSuggestedNewDraftConnectionId,
                StringComparison.Ordinal);
    }

    private string BuildUniqueNewDraftConnectionId(
        string sourceNodeId,
        string targetNodeId)
    {
        var baseId = BuildNewDraftConnectionIdBase(sourceNodeId, targetNodeId);
        var existingIds = WorkflowDefinitionDraftStructure?.Connections
            .Select(connection => connection.ConnectionId)
            .ToHashSet(StringComparer.Ordinal)
            ?? new HashSet<string>(StringComparer.Ordinal);

        var candidate = baseId;
        var suffix = 2;
        while (existingIds.Contains(candidate))
        {
            candidate = $"{baseId}_{suffix}";
            suffix++;
        }

        return candidate;
    }

    private static string BuildNewDraftConnectionIdBase(
        string sourceNodeId,
        string targetNodeId)
    {
        return
            $"{BuildSnakeCaseIdentifier(sourceNodeId, "source")}_to_{BuildSnakeCaseIdentifier(targetNodeId, "target")}";
    }

    private static string BuildSnakeCaseIdentifier(string source, string fallback)
    {
        var builder = new StringBuilder();
        for (var index = 0; index < source.Length; index++)
        {
            var current = source[index];
            if (char.IsLetterOrDigit(current))
            {
                var previous = index > 0 ? source[index - 1] : '\0';
                var next = index + 1 < source.Length ? source[index + 1] : '\0';
                var shouldSeparate =
                    char.IsUpper(current)
                    && builder.Length > 0
                    && builder[^1] != '_'
                    && (char.IsLower(previous)
                        || char.IsDigit(previous)
                        || char.IsLower(next));

                if (shouldSeparate)
                {
                    builder.Append('_');
                }

                builder.Append(char.ToLowerInvariant(current));
            }
            else if (builder.Length > 0 && builder[^1] != '_')
            {
                builder.Append('_');
            }
        }

        return builder.ToString().Trim('_') is { Length: > 0 } value
            ? value
            : fallback;
    }

    private void RefreshShellNavigationItems()
    {
        ShellNavigationItems.Clear();
        foreach (var descriptor in BuiltinShellPages.All.OrderBy(page => page.SortOrder))
        {
            ShellNavigationItems.Add(
                new ShellNavigationItemViewModel(
                    descriptor,
                    ResolveShellPageHeaderText(descriptor)));
        }

        SynchronizeSelectedShellPageIndex(SelectedShellPageKey);
        NotifyShellNavigationItemsChanged();
    }

    private ShellNavigationItemViewModel GetShellNavigationItem(ShellPageKey key)
    {
        return ShellNavigationItems.FirstOrDefault(item => item.Key == key)
            ?? throw new InvalidOperationException($"Shell navigation item '{key}' was not found.");
    }

    private int GetShellNavigationItemIndex(ShellPageKey key)
    {
        for (var index = 0; index < ShellNavigationItems.Count; index++)
        {
            if (ShellNavigationItems[index].Key == key)
            {
                return index;
            }
        }

        throw new InvalidOperationException($"Shell navigation item '{key}' was not found.");
    }

    private static bool IsKnownShellPageKey(ShellPageKey key)
    {
        return BuiltinShellPages.All.Any(page => page.Key == key);
    }

    private bool IsKnownShellPageIndex(int index)
    {
        return index >= 0 && index < ShellNavigationItems.Count;
    }

    private void SynchronizeSelectedShellPageIndex(ShellPageKey key)
    {
        var index = GetShellNavigationItemIndex(key);
        if (SelectedShellPageIndex == index)
        {
            return;
        }

        isSynchronizingShellSelection = true;
        try
        {
            SelectedShellPageIndex = index;
        }
        finally
        {
            isSynchronizingShellSelection = false;
        }
    }

    private void SynchronizeSelectedShellPageKey(int index)
    {
        var key = ShellNavigationItems[index].Key;
        if (SelectedShellPageKey == key)
        {
            return;
        }

        isSynchronizingShellSelection = true;
        try
        {
            SelectedShellPageKey = key;
        }
        finally
        {
            isSynchronizingShellSelection = false;
        }
    }

    private void NotifyShellNavigationItemsChanged()
    {
        OnPropertyChanged(nameof(ShellNavigationItems));
        OnPropertyChanged(nameof(WorkflowsNavigationItem));
        OnPropertyChanged(nameof(RunsNavigationItem));
        OnPropertyChanged(nameof(DataNavigationItem));
        OnPropertyChanged(nameof(LogsNavigationItem));
        OnPropertyChanged(nameof(SettingsNavigationItem));
        OnPropertyChanged(nameof(SelectedShellNavigationItem));
        OnPropertyChanged(nameof(SelectedShellPageContentKey));
        OnPropertyChanged(nameof(SelectedShellPageIndex));
    }

    private string ResolveShellPageHeaderText(ShellPageDescriptor descriptor)
    {
        return descriptor.HeaderPropertyName switch
        {
            nameof(WorkflowsSectionText) => WorkflowsSectionText,
            nameof(RunsSectionText) => RunsSectionText,
            nameof(DataTabText) => DataTabText,
            nameof(LogsTabText) => LogsTabText,
            nameof(SettingsMenuText) => SettingsMenuText,
            _ => throw new InvalidOperationException(
                $"Unknown shell page header property '{descriptor.HeaderPropertyName}'."),
        };
    }

    private Dictionary<string, string> CaptureDefaultMessageSnapshot()
    {
        return new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["status.disconnected"] = T("status.disconnected"),
            ["status.event_stream_disconnected"] = T("status.event_stream_disconnected"),
            ["workflow.default_name"] = T("workflow.default_name"),
            ["status.no_workflows_loaded"] = T("status.no_workflows_loaded"),
            ["status.select_workflow_definition"] = T("status.select_workflow_definition"),
            ["status.no_node_definitions_loaded"] = T("status.no_node_definitions_loaded"),
            ["status.load_definition_to_edit"] = T("status.load_definition_to_edit"),
            ["status.no_runs_loaded"] = T("status.no_runs_loaded"),
            ["status.select_run_node_status"] = T("status.select_run_node_status"),
            ["status.no_runtime_events_loaded"] = T("status.no_runtime_events_loaded"),
            ["status.no_audit_events_loaded"] = T("status.no_audit_events_loaded"),
            ["status.select_run_table_refs"] = T("status.select_run_table_refs"),
            ["status.select_run_and_workflow_node_data_preview"] =
                T("status.select_run_and_workflow_node_data_preview"),
            ["status.no_shared_publications_loaded"] = T("status.no_shared_publications_loaded"),
            ["status.select_share_versions"] = T("status.select_share_versions"),
        };
    }

    private void RefreshDefaultMessagesForCurrentLanguage(
        IReadOnlyDictionary<string, string>? previousDefaults)
    {
        if (ShouldRefreshDefault(StatusMessage, previousDefaults, "status.disconnected"))
        {
            StatusMessage = T("status.disconnected");
        }

        if (ShouldRefreshDefault(
            RuntimeEventStreamMessage,
            previousDefaults,
            "status.event_stream_disconnected"))
        {
            RuntimeEventStreamMessage = T("status.event_stream_disconnected");
        }

        if (ShouldRefreshDefault(NewWorkflowName, previousDefaults, "workflow.default_name"))
        {
            NewWorkflowName = T("workflow.default_name");
        }

        if (ShouldRefreshDefault(WorkflowMessage, previousDefaults, "status.no_workflows_loaded"))
        {
            WorkflowMessage = T("status.no_workflows_loaded");
        }

        if (ShouldRefreshDefault(
            WorkflowDefinitionMessage,
            previousDefaults,
            "status.select_workflow_definition"))
        {
            WorkflowDefinitionMessage = T("status.select_workflow_definition");
        }

        if (ShouldRefreshDefault(
            NodeDefinitionCatalogMessage,
            previousDefaults,
            "status.no_node_definitions_loaded"))
        {
            NodeDefinitionCatalogMessage = T("status.no_node_definitions_loaded");
        }

        if (ShouldRefreshDefault(
            WorkflowDefinitionValidationMessage,
            previousDefaults,
            "status.load_definition_to_edit"))
        {
            WorkflowDefinitionValidationMessage = T("status.load_definition_to_edit");
        }

        if (ShouldRefreshDefault(RunMessage, previousDefaults, "status.no_runs_loaded"))
        {
            RunMessage = T("status.no_runs_loaded");
        }

        if (ShouldRefreshDefault(NodeRunMessage, previousDefaults, "status.select_run_node_status"))
        {
            NodeRunMessage = T("status.select_run_node_status");
        }

        if (ShouldRefreshDefault(
            RuntimeEventLogMessage,
            previousDefaults,
            "status.no_runtime_events_loaded"))
        {
            RuntimeEventLogMessage = T("status.no_runtime_events_loaded");
        }

        if (ShouldRefreshDefault(
            AuditEventLogMessage,
            previousDefaults,
            "status.no_audit_events_loaded"))
        {
            AuditEventLogMessage = T("status.no_audit_events_loaded");
        }

        if (ShouldRefreshDefault(TableRefMessage, previousDefaults, "status.select_run_table_refs"))
        {
            TableRefMessage = T("status.select_run_table_refs");
        }

        if (ShouldRefreshDefault(
            DataPreviewMessage,
            previousDefaults,
            "status.select_run_and_workflow_node_data_preview"))
        {
            DataPreviewMessage = T("status.select_run_and_workflow_node_data_preview");
        }

        if (ShouldRefreshDefault(
            SharedPublicationMessage,
            previousDefaults,
            "status.no_shared_publications_loaded"))
        {
            SharedPublicationMessage = T("status.no_shared_publications_loaded");
        }

        if (ShouldRefreshDefault(
            SharedPublicationVersionMessage,
            previousDefaults,
            "status.select_share_versions"))
        {
            SharedPublicationVersionMessage = T("status.select_share_versions");
        }
    }

    private static bool ShouldRefreshDefault(
        string currentValue,
        IReadOnlyDictionary<string, string>? previousDefaults,
        string key)
    {
        return previousDefaults is null
            || (previousDefaults.TryGetValue(key, out var previousValue)
                && string.Equals(currentValue, previousValue, StringComparison.Ordinal));
    }

    private void NotifyLocalizedTextChanged()
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
        OnPropertyChanged(nameof(WorkflowsSectionText));
        OnPropertyChanged(nameof(RefreshText));
        OnPropertyChanged(nameof(CloseText));
        OnPropertyChanged(nameof(RunText));
        OnPropertyChanged(nameof(CreateText));
        OnPropertyChanged(nameof(WorkflowNameWatermarkText));
        OnPropertyChanged(nameof(RunsSectionText));
        OnPropertyChanged(nameof(CancelText));
        OnPropertyChanged(nameof(CancelConfirmTitleText));
        OnPropertyChanged(nameof(CancelConfirmMessageText));
        OnPropertyChanged(nameof(NodeRunsSectionText));
        OnPropertyChanged(nameof(WorkflowDefinitionSectionText));
        OnPropertyChanged(nameof(DetailsText));
        OnPropertyChanged(nameof(NameLabelText));
        OnPropertyChanged(nameof(VersionLabelText));
        OnPropertyChanged(nameof(RevisionLabelText));
        OnPropertyChanged(nameof(StatusLabelText));
        OnPropertyChanged(nameof(HashLabelText));
        OnPropertyChanged(nameof(UpdatedLabelText));
        OnPropertyChanged(nameof(NodesSectionText));
        OnPropertyChanged(nameof(WorkflowNodesSectionText));
        OnPropertyChanged(nameof(WorkflowDefinitionDraftNodeCountText));
        OnPropertyChanged(nameof(WorkflowDefinitionBatchSelectedNodeCountText));
        OnPropertyChanged(nameof(NodeConfigSectionText));
        OnPropertyChanged(nameof(ApplyNodeConfigText));
        OnPropertyChanged(nameof(ApplyNodeDisplayNameText));
        OnPropertyChanged(nameof(StructuredEditSectionText));
        OnPropertyChanged(nameof(AddNodeText));
        OnPropertyChanged(nameof(CopyNodeText));
        OnPropertyChanged(nameof(DeleteNodeText));
        OnPropertyChanged(nameof(DeleteSelectedNodesText));
        OnPropertyChanged(nameof(MoveNodeUpText));
        OnPropertyChanged(nameof(MoveNodeDownText));
        OnPropertyChanged(nameof(NodeActionsSectionText));
        OnPropertyChanged(nameof(DataPreviewSectionText));
        OnPropertyChanged(nameof(DataPreviewEmptyText));
        OnPropertyChanged(nameof(DataPreviewPendingText));
        OnPropertyChanged(nameof(DataPreviewRefreshText));
        OnPropertyChanged(nameof(PreviewSelectedNodeText));
        OnPropertyChanged(nameof(NodeInstanceIdText));
        OnPropertyChanged(nameof(NodeTypeText));
        OnPropertyChanged(nameof(NodeVersionText));
        OnPropertyChanged(nameof(DisplayNameText));
        OnPropertyChanged(nameof(ConfigJsonText));
        OnPropertyChanged(nameof(ConnectionsSectionText));
        OnPropertyChanged(nameof(ShowConnectionsText));
        OnPropertyChanged(nameof(AddConnectionText));
        OnPropertyChanged(nameof(DeleteConnectionText));
        OnPropertyChanged(nameof(ConnectionIdText));
        OnPropertyChanged(nameof(SourceNodeText));
        OnPropertyChanged(nameof(SourcePortText));
        OnPropertyChanged(nameof(TargetNodeText));
        OnPropertyChanged(nameof(TargetPortText));
        OnPropertyChanged(nameof(NodeCatalogSectionText));
        OnPropertyChanged(nameof(NodeText));
        OnPropertyChanged(nameof(NodeCatalogEmptyStateText));
        OnPropertyChanged(nameof(InputsText));
        OnPropertyChanged(nameof(OutputsText));
        OnPropertyChanged(nameof(ModeText));
        OnPropertyChanged(nameof(TimeoutText));
        OnPropertyChanged(nameof(DraftJsonSectionText));
        OnPropertyChanged(nameof(ShowAdvancedDraftJsonText));
        OnPropertyChanged(nameof(ValidateText));
        OnPropertyChanged(nameof(SaveText));
        OnPropertyChanged(nameof(WorkflowRunFilterText));
        OnPropertyChanged(nameof(RunIdWatermarkText));
        OnPropertyChanged(nameof(NodeRunFilterText));
        OnPropertyChanged(nameof(NodeRunIdWatermarkText));
        OnPropertyChanged(nameof(EventTypeFilterText));
        OnPropertyChanged(nameof(AfterFilterText));
        OnPropertyChanged(nameof(SequenceWatermarkText));
        OnPropertyChanged(nameof(RuntimeText));
        OnPropertyChanged(nameof(AuditText));
        OnPropertyChanged(nameof(LimitText));
        OnPropertyChanged(nameof(RuntimeEventsSectionText));
        OnPropertyChanged(nameof(AuditEventsSectionText));
        OnPropertyChanged(nameof(TableRefsSectionText));
        OnPropertyChanged(nameof(ShareText));
        OnPropertyChanged(nameof(ShareNameWatermarkText));
        OnPropertyChanged(nameof(VersionsText));
        foreach (var nodeDefinition in NodeDefinitions)
        {
            nodeDefinition.RefreshLocalizedText();
        }

        RefreshShellNavigationItems();
        RefreshWorkflowDefinitionDraftStructureState();
        RefreshSelectedNodeConfigDraftState();
    }

    partial void OnConnectionStatusChanged(ConnectionStatus value)
    {
        OnPropertyChanged(nameof(IsChecking));
        NotifyEngineActionStateChanged();
        CheckConnectionCommand.NotifyCanExecuteChanged();
    }

    partial void OnSelectedShellPageKeyChanging(ShellPageKey value)
    {
        if (!IsKnownShellPageKey(value))
        {
            throw new InvalidOperationException($"Unknown shell page key '{value}'.");
        }
    }

    partial void OnSelectedShellPageKeyChanged(ShellPageKey value)
    {
        if (!isSynchronizingShellSelection)
        {
            SynchronizeSelectedShellPageIndex(value);
        }

        OnPropertyChanged(nameof(SelectedShellNavigationItem));
        OnPropertyChanged(nameof(SelectedShellPageContentKey));
    }

    partial void OnSelectedShellPageIndexChanging(int value)
    {
        if (!IsKnownShellPageIndex(value))
        {
            throw new InvalidOperationException($"Unknown shell page index '{value}'.");
        }
    }

    partial void OnSelectedShellPageIndexChanged(int value)
    {
        if (!isSynchronizingShellSelection)
        {
            SynchronizeSelectedShellPageKey(value);
        }
    }

    partial void OnTokenChanged(string value)
    {
        IsAuthenticationFailed = false;
        NotifyEngineActionStateChanged();
    }

    partial void OnBaseUrlChanged(string value)
    {
        IsAuthenticationFailed = false;
        NotifyEngineActionStateChanged();
        CheckConnectionCommand.NotifyCanExecuteChanged();
        StartRuntimeEventStreamCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsRuntimeEventStreamConnectedChanged(bool value)
    {
        NotifyEngineActionStateChanged();
    }

    partial void OnIsAuthenticationFailedChanged(bool value)
    {
        NotifyEngineActionStateChanged();
    }

    partial void OnErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasError));
    }

    partial void OnIsLoadingWorkflowsChanged(bool value)
    {
        NotifyWorkflowCommandStateChanged();
    }

    partial void OnIsStartingWorkflowChanged(bool value)
    {
        NotifyWorkflowCommandStateChanged();
    }

    partial void OnNewWorkflowNameChanged(string value)
    {
        CreateTemplateWorkflowCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsCreatingWorkflowChanged(bool value)
    {
        NotifyWorkflowCommandStateChanged();
    }

    partial void OnSelectedWorkflowChanged(WorkflowListItemViewModel? value)
    {
        workflowDefinitionLoadVersion++;
        StartSelectedWorkflowCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
        LoadSelectedWorkflowDefinitionCommand.NotifyCanExecuteChanged();
        Runs.Clear();
        SelectedRun = null;
        RunMessage = value is null
            ? T("runs.no_workflow_selected")
            : F("format.selected_workflow_refresh_runs", value.Name);
        RunErrorMessage = null;
        if (WorkflowDefinitionDetail?.WorkflowId != value?.WorkflowId)
        {
            WorkflowDefinitionDetail = null;
            SelectedWorkflowDefinitionNode = null;
            originalWorkflowDefinitionJson = string.Empty;
            WorkflowDefinitionDraftJson = string.Empty;
            IsWorkflowDefinitionDraftDirty = false;
            HasWorkflowDefinitionRevisionConflict = false;
            WorkflowDefinitionMessage = value is null
                ? T("status.select_workflow_definition")
                : F("format.selected_workflow_load_definition", value.Name);
        }

        WorkflowDefinitionErrorMessage = null;
        WorkflowDefinitionValidationMessage = value is null
            ? T("status.load_definition_to_edit")
            : T("definition.load_before_editing");
        WorkflowDefinitionValidationErrorMessage = null;
        if (value is not null
            && Workflows.Contains(value)
            && !IsLoadingWorkflows
            && CanLoadSelectedWorkflowDefinition())
        {
            LoadSelectedWorkflowDefinitionCommand.Execute(null);
        }
    }

    partial void OnWorkflowErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasWorkflowError));
    }

    partial void OnLastStartedRunIdChanged(string? value)
    {
        OnPropertyChanged(nameof(HasLastStartedRun));
    }

    partial void OnIsLoadingWorkflowDefinitionChanged(bool value)
    {
        LoadSelectedWorkflowDefinitionCommand.NotifyCanExecuteChanged();
    }

    partial void OnWorkflowDefinitionDetailChanged(WorkflowDefinitionDetailViewModel? value)
    {
        ClearWorkflowDefinitionDraftBatchSelection();
        ResetWorkflowDefinitionStructuredEditInput();
        OnPropertyChanged(nameof(HasWorkflowDefinition));
        RefreshSelectedNodeDisplayNameDraftState();
        RefreshSelectedNodeConfigDraftState();
        ApplySelectedNodeDisplayNameDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
        AddWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
        NotifyWorkflowDefinitionNodeActionCommandsChanged();
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        DeleteWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        SaveWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
    }

    partial void OnSelectedWorkflowDefinitionNodeChanged(
        WorkflowDefinitionNodeListItemViewModel? value)
    {
        OnPropertyChanged(nameof(HasSelectedWorkflowDefinitionNode));
        OnPropertyChanged(nameof(HasNoSelectedWorkflowDefinitionNode));
        ResetDataPreviewSelectionState();
        RefreshSelectedNodeDisplayNameDraftState();
        RefreshSelectedNodeConfigDraftState();
        ApplySelectedNodeDisplayNameDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
        NotifyWorkflowDefinitionNodeActionCommandsChanged();
        RefreshSelectedWorkflowNodeDataPreviewCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
    }

    partial void OnWorkflowDefinitionErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasWorkflowDefinitionError));
    }

    partial void OnIsLoadingNodeDefinitionsChanged(bool value)
    {
        OnPropertyChanged(nameof(HasNodeDefinitionCatalogEmptyState));
        OnPropertyChanged(nameof(RefreshNodeDefinitionsDisabledReasonText));
        RefreshNodeDefinitionsCommand.NotifyCanExecuteChanged();
    }

    partial void OnNodeDefinitionCatalogErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasNodeDefinitionCatalogError));
    }

    partial void OnWorkflowDefinitionDraftJsonChanged(string value)
    {
        OnPropertyChanged(nameof(HasWorkflowDefinitionDraft));
        RefreshWorkflowDefinitionDraftStructureState();
        RefreshSelectedNodeConfigDraftState();

        IsWorkflowDefinitionDraftDirty = value != originalWorkflowDefinitionJson;

        if (WorkflowDefinitionValidationMessage == T("definition.draft_valid") ||
            WorkflowDefinitionValidationMessage == T("definition.draft_has_issues") ||
            WorkflowDefinitionValidationMessage == T("definition.validation_failed"))
        {
            WorkflowDefinitionValidationMessage = T("definition.validation_invalidated");
            WorkflowDefinitionValidationErrorMessage = null;
        }

        ValidateWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeDisplayNameDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
        AddWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
        NotifyWorkflowDefinitionNodeActionCommandsChanged();
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        DeleteWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        SaveWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
    }

    partial void OnWorkflowDefinitionDraftStructureChanged(
        WorkflowDefinitionDraftStructure? value)
    {
        OnPropertyChanged(nameof(HasWorkflowDefinitionDraftStructure));
        OnPropertyChanged(nameof(WorkflowDefinitionDraftNodeCount));
        OnPropertyChanged(nameof(WorkflowDefinitionDraftConnectionCount));
        OnPropertyChanged(nameof(WorkflowDefinitionDraftNodeCountText));
        OnPropertyChanged(nameof(WorkflowDefinitionBatchSelectedNodeCount));
        OnPropertyChanged(nameof(WorkflowDefinitionBatchSelectedNodeCountText));
        OnPropertyChanged(nameof(WorkflowDefinitionDraftConnectionCountText));
        OnPropertyChanged(nameof(HasWorkflowDefinitionDraftStructureWarnings));
        NotifyWorkflowDefinitionNodeActionCommandsChanged();
    }

    partial void OnIsWorkflowDefinitionDraftDirtyChanged(bool value)
    {
        SaveWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
    }

    partial void OnHasWorkflowDefinitionRevisionConflictChanged(bool value)
    {
        ApplySelectedNodeDisplayNameDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
        AddWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
        NotifyWorkflowDefinitionNodeActionCommandsChanged();
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        DeleteWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        SaveWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsValidatingWorkflowDefinitionDraftChanged(bool value)
    {
        OnPropertyChanged(nameof(IsWorkflowDefinitionDraftBusy));
        ValidateWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeDisplayNameDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
        AddWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
        NotifyWorkflowDefinitionNodeActionCommandsChanged();
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        DeleteWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        SaveWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsSavingWorkflowDefinitionDraftChanged(bool value)
    {
        OnPropertyChanged(nameof(IsWorkflowDefinitionDraftBusy));
        ValidateWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeDisplayNameDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
        AddWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
        NotifyWorkflowDefinitionNodeActionCommandsChanged();
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        DeleteWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        SaveWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
    }

    partial void OnWorkflowDefinitionValidationErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasWorkflowDefinitionValidationError));
    }

    partial void OnSelectedNodeDisplayNameDraftChanged(string value)
    {
        ApplySelectedNodeDisplayNameDraftCommand.NotifyCanExecuteChanged();
    }

    private void NotifyWorkflowDefinitionNodeActionCommandsChanged()
    {
        OpenWorkflowAddNodePanelCommand.NotifyCanExecuteChanged();
        CopyWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
        DeleteWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
        DeleteSelectedWorkflowDefinitionDraftNodesCommand.NotifyCanExecuteChanged();
        MoveSelectedWorkflowDefinitionDraftNodeUpCommand.NotifyCanExecuteChanged();
        MoveSelectedWorkflowDefinitionDraftNodeDownCommand.NotifyCanExecuteChanged();
    }

    partial void OnSelectedNewDraftNodeDefinitionChanged(
        NodeDefinitionListItemViewModel? value)
    {
        if (value is not null)
        {
            ApplySelectedNewDraftNodeDefinition(value);
        }
    }

    partial void OnNewDraftNodeInstanceIdChanged(string value)
    {
        AddWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
    }

    partial void OnNewDraftNodeTypeChanged(string value)
    {
        AddWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
    }

    partial void OnNewDraftNodeVersionChanged(string value)
    {
        AddWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
    }

    partial void OnNewDraftNodeConfigJsonChanged(string value)
    {
        AddWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
    }

    partial void OnSelectedWorkflowDefinitionDraftNodeInstanceIdChanged(string value)
    {
        DeleteWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
    }

    partial void OnSelectedNewDraftConnectionSourceNodeChanged(
        WorkflowDefinitionDraftNode? value)
    {
        if (value is not null)
        {
            ApplySelectedNewDraftConnectionSourceNode(value);
        }
    }

    partial void OnSelectedNewDraftConnectionTargetNodeChanged(
        WorkflowDefinitionDraftNode? value)
    {
        if (value is not null)
        {
            ApplySelectedNewDraftConnectionTargetNode(value);
        }
    }

    partial void OnNewDraftConnectionIdChanged(string value)
    {
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
    }

    partial void OnNewDraftConnectionSourceNodeIdChanged(string value)
    {
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
    }

    partial void OnNewDraftConnectionSourcePortChanged(string value)
    {
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
    }

    partial void OnNewDraftConnectionTargetNodeIdChanged(string value)
    {
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
    }

    partial void OnNewDraftConnectionTargetPortChanged(string value)
    {
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
    }

    partial void OnSelectedWorkflowDefinitionDraftConnectionIdChanged(string value)
    {
        DeleteWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsWorkflowDraftJsonAdvancedVisibleChanged(bool value)
    {
        OnPropertyChanged(nameof(ShowAdvancedDraftJsonText));
    }

    partial void OnIsWorkflowConnectionsAdvancedVisibleChanged(bool value)
    {
        OnPropertyChanged(nameof(ShowConnectionsText));
    }

    partial void OnIsLoadingRunsChanged(bool value)
    {
        NotifyRunCommandStateChanged();
    }

    partial void OnIsCancellingRunChanged(bool value)
    {
        NotifyRunCommandStateChanged();
    }

    partial void OnSelectedRunChanged(
        WorkflowRunListItemViewModel? oldValue,
        WorkflowRunListItemViewModel? newValue)
    {
        var runChanged = !string.Equals(
            oldValue?.WorkflowRunId,
            newValue?.WorkflowRunId,
            StringComparison.Ordinal);
        if (runChanged)
        {
            nodeRunsLoadVersion++;
            tableRefsLoadVersion++;
            IsLoadingNodeRuns = false;
            IsLoadingTableRefs = false;
            NodeRuns.Clear();
            TableRefs.Clear();
            NodeRunMessage = newValue is null
                ? T("status.select_run_node_status")
                : F("format.selected_run_refresh_nodes", newValue.WorkflowRunId);
            NodeRunErrorMessage = null;
            TableRefMessage = newValue is null
                ? T("status.select_run_table_refs")
                : F("format.selected_run_refresh_table_refs", newValue.WorkflowRunId);
            TableRefErrorMessage = null;
            ResetDataPreviewSelectionState();
        }
        else
        {
            RefreshSelectedWorkflowNodeDataPreviewCommand.NotifyCanExecuteChanged();
        }

        NotifyEngineActionStateChanged();
        RefreshNodeRunsCommand.NotifyCanExecuteChanged();
        RefreshTableRefsCommand.NotifyCanExecuteChanged();
    }

    partial void OnRunErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasRunError));
    }

    partial void OnIsLoadingNodeRunsChanged(bool value)
    {
        OnPropertyChanged(nameof(IsNodeRunBusy));
        RefreshNodeRunsCommand.NotifyCanExecuteChanged();
    }

    partial void OnNodeRunErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasNodeRunError));
    }

    partial void OnIsRuntimeEventStreamRunningChanged(bool value)
    {
        StartRuntimeEventStreamCommand.NotifyCanExecuteChanged();
        StopRuntimeEventStreamCommand.NotifyCanExecuteChanged();
    }

    partial void OnRuntimeEventStreamErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasRuntimeEventStreamError));
    }

    partial void OnIsLoadingRuntimeEventLogChanged(bool value)
    {
        OnPropertyChanged(nameof(IsLogBusy));
        RefreshRuntimeEventLogCommand.NotifyCanExecuteChanged();
    }

    partial void OnRuntimeEventLogErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasRuntimeEventLogError));
    }

    partial void OnIsLoadingAuditEventLogChanged(bool value)
    {
        OnPropertyChanged(nameof(IsLogBusy));
        RefreshAuditEventsCommand.NotifyCanExecuteChanged();
    }

    partial void OnAuditEventLogErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasAuditEventLogError));
    }

    partial void OnIsLoadingTableRefsChanged(bool value)
    {
        OnPropertyChanged(nameof(IsDataBusy));
        RefreshTableRefsCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsLoadingDataPreviewChanged(bool value)
    {
        OnPropertyChanged(nameof(IsDataPreviewBusy));
        RefreshSelectedWorkflowNodeDataPreviewCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
    }

    partial void OnTableRefErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasTableRefError));
    }

    partial void OnDataPreviewErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasDataPreviewError));
    }

    partial void OnIsLoadingSharedPublicationsChanged(bool value)
    {
        OnPropertyChanged(nameof(IsDataBusy));
        RefreshSharedPublicationsCommand.NotifyCanExecuteChanged();
    }

    partial void OnSelectedSharedPublicationChanged(SharedPublicationListItemViewModel? value)
    {
        sharedPublicationVersionsLoadVersion++;
        IsLoadingSharedPublicationVersions = false;
        SharedPublicationVersions.Clear();
        SharedPublicationVersionMessage = string.Empty;
        SharedPublicationVersionErrorMessage = null;

        if (value is not null)
        {
            SharedPublicationVersionShareNameFilter = value.ShareName;
        }

        RefreshSharedPublicationVersionsCommand.NotifyCanExecuteChanged();
    }

    partial void OnSharedPublicationVersionShareNameFilterChanged(string value)
    {
        RefreshSharedPublicationVersionsCommand.NotifyCanExecuteChanged();
    }

    partial void OnLogWorkflowRunIdFilterChanged(string value)
    {
        InvalidateLogLoads();
    }

    partial void OnLogNodeRunIdFilterChanged(string value)
    {
        InvalidateLogLoads();
    }

    partial void OnLogEventTypeFilterChanged(string value)
    {
        InvalidateLogLoads();
    }

    private void InvalidateLogLoads()
    {
        runtimeEventLogLoadVersion++;
        auditEventLogLoadVersion++;
        IsLoadingRuntimeEventLog = false;
        IsLoadingAuditEventLog = false;
        RefreshRuntimeEventLogCommand.NotifyCanExecuteChanged();
        RefreshAuditEventsCommand.NotifyCanExecuteChanged();
    }

    partial void OnSharedPublicationErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasSharedPublicationError));
    }

    partial void OnIsLoadingSharedPublicationVersionsChanged(bool value)
    {
        OnPropertyChanged(nameof(IsDataBusy));
        RefreshSharedPublicationVersionsCommand.NotifyCanExecuteChanged();
    }

    partial void OnSharedPublicationVersionErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasSharedPublicationVersionError));
    }

    private void NotifyWorkflowCommandStateChanged()
    {
        OnPropertyChanged(nameof(IsWorkflowBusy));
        RefreshWorkflowsCommand.NotifyCanExecuteChanged();
        CreateTemplateWorkflowCommand.NotifyCanExecuteChanged();
        StartSelectedWorkflowCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
    }

    private void NotifyRunCommandStateChanged()
    {
        OnPropertyChanged(nameof(IsRunBusy));
        NotifyEngineActionStateChanged();
        RefreshRunsCommand.NotifyCanExecuteChanged();
    }

    private void NotifyEngineActionStateChanged()
    {
        OnPropertyChanged(nameof(CanUseEngineActions));
        OnPropertyChanged(nameof(CanUseCancelSelectedRunAction));
        OnPropertyChanged(nameof(CancelSelectedRunDisabledReasonText));
        OnPropertyChanged(nameof(RefreshNodeDefinitionsDisabledReasonText));
        RefreshWorkflowsCommand.NotifyCanExecuteChanged();
        CreateTemplateWorkflowCommand.NotifyCanExecuteChanged();
        StartSelectedWorkflowCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
        RefreshRunsCommand.NotifyCanExecuteChanged();
        CancelSelectedRunCommand.NotifyCanExecuteChanged();
        RefreshNodeRunsCommand.NotifyCanExecuteChanged();
        LoadSelectedWorkflowDefinitionCommand.NotifyCanExecuteChanged();
        RefreshNodeDefinitionsCommand.NotifyCanExecuteChanged();
        ValidateWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
        AddWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
        NotifyWorkflowDefinitionNodeActionCommandsChanged();
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        DeleteWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        SaveWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        RefreshRuntimeEventLogCommand.NotifyCanExecuteChanged();
        RefreshAuditEventsCommand.NotifyCanExecuteChanged();
        RefreshTableRefsCommand.NotifyCanExecuteChanged();
        RefreshSelectedWorkflowNodeDataPreviewCommand.NotifyCanExecuteChanged();
        RefreshSharedPublicationsCommand.NotifyCanExecuteChanged();
        RefreshSharedPublicationVersionsCommand.NotifyCanExecuteChanged();
    }

    private static bool IsCancelableRunStatus(string? status)
    {
        return status == "RUNNING";
    }

    private static bool IsTerminalRunStatus(string? status)
    {
        return status is "SUCCEEDED" or "FAILED" or "CANCELLED" or "ABORTED";
    }

    private static bool IsActiveWorkflowStatus(string? status)
    {
        return status == "ACTIVE";
    }
}

internal static class TemplateWorkflowDefinitions
{
    public static JsonDocument CreateGeneratedTable(
        string generateRowsDisplayName,
        string keepAmountGreaterThanOneDisplayName)
    {
        var definition = new
        {
            schema_version = "1.0",
            nodes = new object[]
            {
                new
                {
                    node_instance_id = "generate",
                    node_type = "GenerateTestTableNode",
                    node_version = "1.0",
                    display_name = generateRowsDisplayName,
                    config = new
                    {
                        rows = 3,
                        columns = new[] { "row_id", "amount" },
                        seed = 0,
                    },
                },
                new
                {
                    node_instance_id = "filter",
                    node_type = "FilterRowsNode",
                    node_version = "1.0",
                    display_name = keepAmountGreaterThanOneDisplayName,
                    config = new
                    {
                        field = "amount",
                        @operator = "GT",
                        value = 1.0,
                    },
                },
            },
            connections = new[]
            {
                new
                {
                    connection_id = "generate_to_filter",
                    source_node_id = "generate",
                    source_port = "out",
                    target_node_id = "filter",
                    target_port = "in",
                },
            },
        };

        return JsonSerializer.SerializeToDocument(definition, FlowWeaverJson.Options);
    }
}
