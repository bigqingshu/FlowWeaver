using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Globalization;
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
    private const int DataPreviewRowLimit = 50;
    private const int DataPreviewRunRefreshAttemptCount = 8;
    private static readonly string[] RuntimeOptionsProfileValues =
        ["normal", "background_fast", "diagnostic", "custom"];
    private static readonly string[] RuntimeOptionsLogLevelValues =
        ["DEBUG", "INFO", "WARN", "ERROR"];
    private static readonly string[] RuntimeOptionsEventLevelValues =
        ["none", "basic", "progress", "verbose"];
    private static readonly string[] RuntimeOptionsMaskPolicyValues =
        ["none", "partial", "full"];

    private readonly IEngineHostApiClient _apiClient;
    private readonly Func<CancellationToken, Task> _dataPreviewRunRefreshDelay;
    private readonly IUiSettingsStore _uiSettingsStore;
    private readonly ILocalizationService _localizationService;
    private readonly NodeEditorResolver _nodeEditorResolver = new(BuiltinNodeEditors.CreateRegistry());

    private readonly CancellationTokenSource _shutdown = new();
    private int nodeDefinitionsLoadVersion;
    private int tableRefsLoadVersion;
    private int sharedPublicationsLoadVersion;
    private int sharedPublicationVersionsLoadVersion;
    private int dataPreviewLoadVersion;
    private int dataPreviewWorkbenchLoadVersion;
    private int runtimeEventLogLoadVersion;

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

    [ObservableProperty]
    private WorkflowDefinitionNodeListItemViewModel? selectedRuntimeOptionsNode;

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeProfileDraft = RuntimeOptionsDefaults.Profile;

    [ObservableProperty]
    private bool runtimeOptionsSelectedNodeStrictValidationDraft = true;

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeLogLevelDraft =
        RuntimeOptionsDefaults.LogLevel;

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeEventLevelDraft =
        RuntimeOptionsDefaults.EventLevel;

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeEventRateLimitPerSecondDraft = "0";

    [ObservableProperty]
    private bool runtimeOptionsSelectedNodeProgressEnabledDraft = true;

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeProgressIntervalSecondsDraft = "0";

    [ObservableProperty]
    private bool runtimeOptionsSelectedNodeCaptureErrorContextDraft = true;

    [ObservableProperty]
    private bool runtimeOptionsSelectedNodeIncludeMetricsDraft = true;

    [ObservableProperty]
    private string runtimeOptionsSelectedNodePayloadByteLimitDraft = "0";

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeTtlSecondsDraft = "0";

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeRedactColumnsDraft = string.Empty;

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeMaskPolicyDraft =
        RuntimeOptionsDefaults.MaskPolicy;

    [ObservableProperty]
    private int runtimeOptionsNodeOverrideCount;

    [ObservableProperty]
    private string? runtimeOptionsEditorErrorMessage;

    [ObservableProperty]
    private bool isRuntimeOptionsJsonEditorExpanded;

    [ObservableProperty]
    private string runtimeOptionsJsonDraft = string.Empty;

    [ObservableProperty]
    private bool isRuntimeOptionsJsonDraftDirty;

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
    private bool isSynchronizingRuntimeOptionsJsonDraft;

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
    private TableRefListItemViewModel? selectedDataPreviewTableRef;

    [ObservableProperty]
    private DataPreviewStateListItemViewModel? selectedDataPreviewState;

    [ObservableProperty]
    private TableRefListItemViewModel? selectedDataPreviewTableOption;

    [ObservableProperty]
    private TableRefListItemViewModel? loadedDataPreviewTableRef;

    [ObservableProperty]
    private bool isLoadingDataPreviewWorkbench;

    [ObservableProperty]
    private string dataPreviewWorkbenchMessage =
        "Select a run, refresh table refs, then select a table to inspect rows.";

    [ObservableProperty]
    private string? dataPreviewWorkbenchErrorMessage;

    [ObservableProperty]
    private string dataPreviewWorkbenchSearchText = string.Empty;

    [ObservableProperty]
    private string dataPreviewWorkbenchClipboardText = string.Empty;

    [ObservableProperty]
    private string dataPreviewWorkbenchPasteText = string.Empty;

    [ObservableProperty]
    private bool isDataPreviewWorkbenchDraft;

    private string? dataPreviewSourceWorkflowRunId;

    private string? dataPreviewSourceNodeInstanceId;

    private string? dataPreviewSourceLogicalTableId;

    private string? dataPreviewSourceTableRefId;

    private string? dataPreviewSourceRunMode;

    private string? dataPreviewSourceTargetNodeInstanceId;

    private string[] dataPreviewWorkbenchLoadedColumns = [];

    private JsonElement[] dataPreviewWorkbenchLoadedRows = [];

    private string[][] dataPreviewWorkbenchOriginalCellRows = [];

    private string[][] dataPreviewWorkbenchEditableCellRows = [];

    private int dataPreviewWorkbenchOffset;

    private bool dataPreviewWorkbenchHasMore;

    private long dataPreviewWorkbenchRowCount;

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

    public ObservableCollection<NodeDefinitionListItemViewModel> NodeDefinitions { get; } =
        new();

    public ObservableCollection<WorkflowDefinitionNodeListItemViewModel>
        WorkflowDefinitionDraftNodes { get; } = new();

    public IReadOnlyList<NodeConfigOptionItemViewModel> RuntimeOptionsProfileOptions =>
        CreateRuntimeOptionsOptions("profile", RuntimeOptionsProfileValues);

    public IReadOnlyList<NodeConfigOptionItemViewModel> RuntimeOptionsLogLevelOptions =>
        CreateRuntimeOptionsOptions("log_level", RuntimeOptionsLogLevelValues);

    public IReadOnlyList<NodeConfigOptionItemViewModel> RuntimeOptionsEventLevelOptions =>
        CreateRuntimeOptionsOptions("event_level", RuntimeOptionsEventLevelValues);

    public IReadOnlyList<NodeConfigOptionItemViewModel> RuntimeOptionsMaskPolicyOptions =>
        CreateRuntimeOptionsOptions("mask_policy", RuntimeOptionsMaskPolicyValues);

    public ObservableCollection<NodeConfigEditableFieldInputViewModel>
        SelectedNodeConfigEditableInputFields { get; } = new();

    public ObservableCollection<RuntimeEventListItemViewModel> RuntimeEventLogEntries { get; } = new();

    public ObservableCollection<TableRefListItemViewModel> TableRefs { get; } = new();

    public ObservableCollection<DataPreviewStateListItemViewModel> DataPreviewStates { get; } = new();

    public ObservableCollection<TableRefListItemViewModel> DataPreviewTableOptions { get; } = new();

    public ObservableCollection<TableDataPreviewColumnViewModel> DataPreviewColumns { get; } = new();

    public ObservableCollection<TableDataPreviewRowViewModel> DataPreviewRows { get; } =
        new();

    public ObservableCollection<TableDataPreviewColumnViewModel> DataPreviewWorkbenchColumns { get; } = new();

    public ObservableCollection<TableDataPreviewRowViewModel> DataPreviewWorkbenchRows { get; } =
        new();

    public ObservableCollection<SharedPublicationListItemViewModel> SharedPublications { get; } =
        new();

    public ObservableCollection<SharedPublicationListItemViewModel> SharedPublicationVersions { get; } =
        new();

    private DisplayTextFormatter DisplayTextFormatter => new(_localizationService);

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

    public bool HasSelectedRuntimeOptionsNode => SelectedRuntimeOptionsNode is not null;

    public bool HasRuntimeOptionsEditorError =>
        !string.IsNullOrWhiteSpace(RuntimeOptionsEditorErrorMessage);

    public string RuntimeOptionsSummaryText =>
        F(
            "definition.runtime_options_summary",
            FormatRuntimeOptionsOptionValue("profile", RuntimeOptionsProfileDraft),
            FormatRuntimeOptionsOptionValue("event_level", RuntimeOptionsEventLevelDraft),
            RuntimeOptionsProgressEnabledDraft ? T("common.on") : T("common.off"),
            RuntimeOptionsNodeOverrideCount);

    public bool HasSelectedRunRuntimeOptionsSummary => SelectedRun is not null;

    public string SelectedRunRuntimeOptionsSummaryText =>
        FormatSelectedRunRuntimeOptionsSummary();

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

    public bool HasRuntimeEventLogError =>
        !string.IsNullOrWhiteSpace(RuntimeEventLogErrorMessage);

    public bool IsLogBusy => IsLoadingRuntimeEventLog;

    public bool HasTableRefError => !string.IsNullOrWhiteSpace(TableRefErrorMessage);

    public bool HasDataPreviewError =>
        !string.IsNullOrWhiteSpace(DataPreviewErrorMessage);

    public bool HasDataPreviewWorkbenchError =>
        !string.IsNullOrWhiteSpace(DataPreviewWorkbenchErrorMessage);

    public bool HasDataPreviewColumns => DataPreviewColumns.Count > 0;

    public bool HasDataPreviewRows => DataPreviewRows.Count > 0;

    public bool HasDataPreviewWorkbenchColumns => DataPreviewWorkbenchColumns.Count > 0;

    public bool HasDataPreviewWorkbenchRows => DataPreviewWorkbenchRows.Count > 0;

    public bool HasDataPreviewWorkbenchClipboardText =>
        !string.IsNullOrEmpty(DataPreviewWorkbenchClipboardText);

    public bool HasDataPreviewWorkbenchPasteText =>
        !string.IsNullOrWhiteSpace(DataPreviewWorkbenchPasteText);

    public bool IsDataPreviewWorkbenchDirty =>
        dataPreviewWorkbenchEditableCellRows.Length > 0
        && !DataPreviewWorkbenchCellRowsEqual(
            dataPreviewWorkbenchOriginalCellRows,
            dataPreviewWorkbenchEditableCellRows);

    public string DataPreviewWorkbenchDirtyStateText => IsDataPreviewWorkbenchDirty
        ? T("data_preview.dirty")
        : T("data_preview.clean");

    public bool CanSaveDataPreviewWorkbenchAsDraft =>
        LoadedDataPreviewTableRef?.HasCapability("SAVE_AS") == true;

    public string DataPreviewWorkbenchSavePolicyText =>
        LoadedDataPreviewTableRef is not { } tableRef
            ? T("data_preview.save_policy_local_draft")
            : CanSaveDataPreviewWorkbenchAsDraft
                ? F(
                    "format.data_preview_save_policy_save_as",
                    tableRef.StorageKind,
                    tableRef.CapabilitiesText)
                : F(
                    "format.data_preview_save_policy_read_only",
                    tableRef.StorageKind,
                    tableRef.CapabilitiesText);

    public string DataPreviewWorkbenchPageText => F(
        "format.data_preview_workbench_page",
        dataPreviewWorkbenchLoadedRows.Length == 0 ? 0 : dataPreviewWorkbenchOffset + 1,
        dataPreviewWorkbenchOffset + dataPreviewWorkbenchLoadedRows.Length,
        dataPreviewWorkbenchRowCount);

    public string DataPreviewSourceText =>
        !string.IsNullOrWhiteSpace(dataPreviewSourceWorkflowRunId)
        && !string.IsNullOrWhiteSpace(dataPreviewSourceNodeInstanceId)
        && !string.IsNullOrWhiteSpace(dataPreviewSourceLogicalTableId)
            ? FormatDataPreviewSourceText()
            : T("data_preview.source_not_loaded");

    public bool HasSharedPublicationError =>
        !string.IsNullOrWhiteSpace(SharedPublicationErrorMessage);

    public bool HasSharedPublicationVersionError =>
        !string.IsNullOrWhiteSpace(SharedPublicationVersionErrorMessage);

    public bool IsDataBusy =>
        IsLoadingTableRefs || IsLoadingSharedPublications || IsLoadingSharedPublicationVersions;

    public bool IsDataPreviewBusy => IsLoadingDataPreview;

    public bool IsDataPreviewWorkbenchBusy => IsLoadingDataPreviewWorkbench;

    public string ExecutionTabText => T("tab.execution");

    public string DefinitionTabText => T("tab.definition");

    public string LogsTabText => T("tab.logs");

    public string DataTabText => T("tab.data");

    public string DataPreviewTabText => T("tab.data_preview");

    public string DataPreviewWorkbenchPendingText => T("data_preview.workbench_pending");

    public string DataPreviewWorkbenchSourceText =>
        IsDataPreviewWorkbenchDraft
            ? T("data_preview.workbench_draft_source")
            : LoadedDataPreviewTableRef is not { } tableRef
            ? T("data_preview.workbench_source_not_loaded")
            : F(
                "format.data_preview_workbench_source",
                tableRef.WorkflowRunId,
                tableRef.NodeRunId,
                tableRef.LogicalTableId,
                tableRef.StorageKind);

    public string DataPreviewTableSelectorText => T("data_preview.table_selector");

    public string DataPreviewStateSelectorText => T("data_preview.state_selector");

    public string DataPreviewLoadSelectedTableText => T("data_preview.load_selected_table");

    public string DataPreviewWorkbenchRefreshText => T("data_preview.workbench_refresh");

    public string DataPreviewDetailsText => T("data_preview.details");

    public string DataPreviewSearchText => T("data_preview.search");

    public string DataPreviewSearchWatermarkText => T("data_preview.search_watermark");

    public string DataPreviewCopyTsvText => T("data_preview.copy_tsv");

    public string DataPreviewPasteText => T("data_preview.paste_text");

    public string DataPreviewPasteWatermarkText => T("data_preview.paste_watermark");

    public string DataPreviewParsePasteText => T("data_preview.parse_paste");

    public string DataPreviewRestoreDraftText => T("data_preview.restore_draft");

    public string DataPreviewSaveAsText => T("data_preview.save_as");

    public string DataPreviewPreviousPageText => T("data_preview.previous_page");
    public string DataPreviewNextPageText => T("data_preview.next_page");

    public string WorkflowsSectionText => T("workflow.section");

    public string RefreshText => T("common.refresh");

    public string CloseText => T("common.close");

    public string RunText => T("workflow.run");

    public string WorkflowRunGuardText
    {
        get
        {
            if (HasWorkflowDefinitionRevisionConflict)
            {
                return T("workflow.run_guard_revision_conflict");
            }

            return IsWorkflowDefinitionDraftDirty
                ? T("workflow.run_guard_dirty_draft")
                : T("workflow.run_guard_saved_revision");
        }
    }

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

    public string RuntimeOptionsSectionText => T("definition.runtime_options");

    public string RuntimeOptionsOpenEditorText =>
        T("definition.runtime_options_open_editor");

    public string RuntimeOptionsWindowTitleText =>
        T("definition.runtime_options_window_title");

    public string RuntimeOptionsWorkflowSectionText =>
        T("definition.runtime_options_workflow_section");

    public string RuntimeOptionsNodeOverrideSectionText =>
        T("definition.runtime_options_node_override_section");

    public string RuntimeOptionsProfileText => T("definition.runtime_options_profile");

    public string RuntimeOptionsStrictValidationText =>
        T("definition.runtime_options_strict_validation");

    public string RuntimeOptionsLogLevelText => T("definition.runtime_options_log_level");

    public string RuntimeOptionsEventLevelText =>
        T("definition.runtime_options_event_level");

    public string RuntimeOptionsEventRateLimitText =>
        T("definition.runtime_options_event_rate_limit");

    public string RuntimeOptionsProgressEnabledText =>
        T("definition.runtime_options_progress_enabled");

    public string RuntimeOptionsProgressIntervalText =>
        T("definition.runtime_options_progress_interval");

    public string RuntimeOptionsCaptureErrorContextText =>
        T("definition.runtime_options_capture_error_context");

    public string RuntimeOptionsIncludeMetricsText =>
        T("definition.runtime_options_include_metrics");

    public string RuntimeOptionsPayloadByteLimitText =>
        T("definition.runtime_options_payload_byte_limit");

    public string RuntimeOptionsTtlSecondsText =>
        T("definition.runtime_options_ttl_seconds");

    public string RuntimeOptionsRedactColumnsText =>
        T("definition.runtime_options_redact_columns");

    public string RuntimeOptionsMaskPolicyText =>
        T("definition.runtime_options_mask_policy");

    public string RuntimeOptionsJsonSectionText =>
        T("definition.runtime_options_json_section");

    public string RuntimeOptionsJsonRegenerateText =>
        T("definition.runtime_options_json_regenerate");

    public string RuntimeOptionsJsonWatermarkText =>
        T("definition.runtime_options_json_watermark");

    public string RuntimeOptionsSelectNodeText =>
        T("definition.runtime_options_select_node");

    public string RuntimeOptionsApplyText => T("definition.runtime_options_apply");

    public string RuntimeOptionsResetNodeOverrideText =>
        T("definition.runtime_options_reset_node_override");

    public string StructuredEditSectionText => T("definition.structured_edit");

    public string AddNodeText => T("definition.add_node");

    public string CopyNodeText => T("definition.copy_node");

    public string DeleteNodeText => T("definition.delete_node");

    public string DeleteSelectedNodesText => T("definition.delete_selected_nodes");

    public string MoveNodeUpText => T("definition.move_node_up");

    public string MoveNodeDownText => T("definition.move_node_down");

    public string NodeActionsSectionText => T("definition.node_actions");

    public string NodeMoveSemanticsText => T("definition.node_move_semantics");

    public string WorkflowLinearChainStatusText
    {
        get
        {
            if (string.IsNullOrWhiteSpace(WorkflowDefinitionDraftJson))
            {
                return T("definition.linear_chain_status_not_loaded");
            }

            var analysis = WorkflowDefinitionLinearChainAnalyzer.Analyze(
                WorkflowDefinitionDraftJson);
            return analysis.IsLinear
                ? F(
                    "definition.linear_chain_status_linear",
                    analysis.NodeInstanceIds.Count)
                : F(
                    "definition.linear_chain_status_not_linear",
                    LocalizeWorkflowDefinitionDraftWarning(analysis.Warning));
        }
    }

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

    public string RestoreText => T("definition.restore");

    public string SaveText => T("definition.save");

    public string WorkflowRunFilterText => T("logs.workflow_run");

    public string RunIdWatermarkText => T("logs.run_id_watermark");

    public string NodeRunFilterText => T("logs.node_run");

    public string NodeRunIdWatermarkText => T("logs.node_run_id_watermark");

    public string EventTypeFilterText => T("logs.event_type");

    public string AfterFilterText => T("logs.after");

    public string SequenceWatermarkText => T("logs.sequence_watermark");

    public string RuntimeText => T("logs.runtime");

    public string LimitText => T("common.limit");

    public string RuntimeEventsSectionText => T("logs.runtime_events");

    public string TableRefsSectionText => T("data.table_refs");

    public string ShareText => T("data.share");

    public string ShareNameWatermarkText => T("data.share_name_watermark");

    public string VersionsText => T("data.versions");

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

    private bool CanRestoreWorkflowDefinitionDraft()
    {
        return HasWorkflowDefinitionDraft
            && IsWorkflowDefinitionDraftDirty
            && !IsWorkflowDefinitionDraftBusy;
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

    private bool CanApplyRuntimeOptionsDraft()
    {
        return HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict;
    }

    private bool CanResetRuntimeOptionsSelectedNodeOverride()
    {
        return CanApplyRuntimeOptionsDraft()
            && SelectedRuntimeOptionsNode is not null;
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

    private string? GetWorkflowDefinitionNodeMutationDisabledReason()
    {
        if (IsWorkflowDefinitionDraftBusy)
        {
            return T("action.disabled.busy");
        }

        if (!CanUseEngineActions)
        {
            return T("action.disabled.engine_not_connected");
        }

        if (WorkflowDefinitionDetail is null || !HasWorkflowDefinitionDraft)
        {
            return T("action.disabled.no_workflow_definition");
        }

        if (HasWorkflowDefinitionRevisionConflict)
        {
            return T("action.disabled.revision_conflict");
        }

        return null;
    }

    private string? GetSelectedWorkflowDefinitionNodeMutationDisabledReason()
    {
        var commonReason = GetWorkflowDefinitionNodeMutationDisabledReason();
        if (commonReason is not null)
        {
            return commonReason;
        }

        if (SelectedWorkflowDefinitionNode is null)
        {
            return T("action.disabled.no_workflow_node_selected");
        }

        if (FindDraftNode(SelectedWorkflowDefinitionNode.NodeInstanceId) is null)
        {
            return T("action.disabled.workflow_node_missing");
        }

        return null;
    }

    private string? GetSelectedWorkflowDefinitionDraftNodesMutationDisabledReason()
    {
        var commonReason = GetWorkflowDefinitionNodeMutationDisabledReason();
        if (commonReason is not null)
        {
            return commonReason;
        }

        var selectedNodes = WorkflowDefinitionDraftNodes
            .Where(node => node.IsBatchSelected)
            .ToArray();
        if (selectedNodes.Length == 0)
        {
            return T("action.disabled.no_workflow_nodes_checked");
        }

        return selectedNodes.Any(node => FindDraftNode(node.NodeInstanceId) is null)
            ? T("action.disabled.workflow_node_missing")
            : null;
    }

    private string? GetMoveSelectedWorkflowDefinitionDraftNodeDisabledReason(int offset)
    {
        var selectedReason = GetSelectedWorkflowDefinitionNodeMutationDisabledReason();
        if (selectedReason is not null)
        {
            return selectedReason;
        }

        var index = WorkflowDefinitionDraftNodes.IndexOf(SelectedWorkflowDefinitionNode!);
        var targetIndex = index + offset;
        if (index < 0)
        {
            return T("action.disabled.workflow_node_missing");
        }

        if (targetIndex < 0)
        {
            return T("action.disabled.workflow_node_at_top");
        }

        return targetIndex >= WorkflowDefinitionDraftNodes.Count
            ? T("action.disabled.workflow_node_at_bottom")
            : null;
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

    public string? CopyWorkflowDefinitionDraftNodeDisabledReasonText =>
        GetSelectedWorkflowDefinitionNodeMutationDisabledReason();

    public string? DeleteWorkflowDefinitionDraftNodeDisabledReasonText =>
        GetSelectedWorkflowDefinitionNodeMutationDisabledReason();

    public string? DeleteSelectedWorkflowDefinitionDraftNodesDisabledReasonText =>
        GetSelectedWorkflowDefinitionDraftNodesMutationDisabledReason();

    public string? MoveSelectedWorkflowDefinitionDraftNodeUpDisabledReasonText =>
        GetMoveSelectedWorkflowDefinitionDraftNodeDisabledReason(offset: -1);

    public string? MoveSelectedWorkflowDefinitionDraftNodeDownDisabledReasonText =>
        GetMoveSelectedWorkflowDefinitionDraftNodeDisabledReason(offset: 1);

    private bool CanRefreshRuntimeEventLog()
    {
        return CanUseEngineActions && !IsLoadingRuntimeEventLog;
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

    private bool CanLoadSelectedDataPreviewTable()
    {
        return CanUseEngineActions
            && SelectedDataPreviewTableOption is not null
            && !IsLoadingDataPreviewWorkbench;
    }

    private bool CanLoadPreviousDataPreviewWorkbenchPage()
    {
        return CanUseEngineActions
            && LoadedDataPreviewTableRef is not null
            && !IsLoadingDataPreviewWorkbench
            && dataPreviewWorkbenchOffset > 0;
    }

    private bool CanLoadNextDataPreviewWorkbenchPage()
    {
        return CanUseEngineActions
            && LoadedDataPreviewTableRef is not null
            && !IsLoadingDataPreviewWorkbench
            && dataPreviewWorkbenchHasMore;
    }

    private bool CanCopyDataPreviewWorkbenchTsv()
    {
        return HasDataPreviewWorkbenchColumns
            && HasDataPreviewWorkbenchRows;
    }

    private bool CanParseDataPreviewWorkbenchPaste()
    {
        return HasDataPreviewWorkbenchPasteText
            && !IsLoadingDataPreviewWorkbench;
    }

    private bool CanRestoreDataPreviewWorkbenchDraft()
    {
        return IsDataPreviewWorkbenchDirty
            && !IsLoadingDataPreviewWorkbench;
    }

    private bool CanSaveDataPreviewWorkbenchAs()
    {
        return IsDataPreviewWorkbenchDirty
            && CanSaveDataPreviewWorkbenchAsDraft
            && !IsLoadingDataPreviewWorkbench;
    }

    private bool CanShowDataPreviewDetails()
    {
        return CanUseEngineActions
            && !string.IsNullOrWhiteSpace(dataPreviewSourceTableRefId)
            && !IsLoadingDataPreviewWorkbench;
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
                DisplayTextFormatter,
                _nodeEditorResolver);
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

                RefreshNodeEditorSchemaFallbackNodes();
                OnPropertyChanged(nameof(HasNodeDefinitions));
                OnPropertyChanged(nameof(HasNodeDefinitionCatalogEmptyState));
                RefreshWorkflowDefinitionDraftStructureState();
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

    [RelayCommand(CanExecute = nameof(CanValidateWorkflowDefinitionDraft))]
    private async Task ValidateWorkflowDefinitionDraftAsync()
    {
        if (string.IsNullOrWhiteSpace(WorkflowDefinitionDraftJson))
        {
            WorkflowDefinitionValidationMessage = T("definition.validation_rejected");
            WorkflowDefinitionValidationErrorMessage = T("definition.draft_required");
            ShowWorkflowDefinitionNotification(
                "workflow.definition.validate",
                UiNotificationKind.Error);
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
            ShowWorkflowDefinitionNotification(
                "workflow.definition.validate",
                UiNotificationKind.Error);
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
            ShowWorkflowDefinitionNotification(
                "workflow.definition.validate",
                response.Data.Valid ? UiNotificationKind.Success : UiNotificationKind.Warning);
            return;
        }

        WorkflowDefinitionValidationMessage = T("definition.validation_failed");
        WorkflowDefinitionValidationErrorMessage = DescribeError(response);
        IsValidatingWorkflowDefinitionDraft = false;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.validate",
            UiNotificationKind.Error);
    }

    [RelayCommand(CanExecute = nameof(CanRestoreWorkflowDefinitionDraft))]
    private void RestoreWorkflowDefinitionDraft()
    {
        if (!CanRestoreWorkflowDefinitionDraft())
        {
            return;
        }

        var selectedNodeId = SelectedWorkflowDefinitionNode?.NodeInstanceId;
        WorkflowDefinitionDraftJson = originalWorkflowDefinitionJson;
        if (!string.IsNullOrWhiteSpace(selectedNodeId))
        {
            SelectWorkflowDefinitionDraftNode(selectedNodeId);
        }

        WorkflowDefinitionValidationMessage = T("definition.draft_restored");
        WorkflowDefinitionValidationErrorMessage = null;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.restore",
            UiNotificationKind.Success);
    }

    [RelayCommand(CanExecute = nameof(CanApplySelectedNodeConfigDraft))]
    private void ApplySelectedNodeConfigDraft()
    {
        if (SelectedWorkflowDefinitionNode is null)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_config_apply_failed");
            WorkflowDefinitionValidationErrorMessage =
                DisplayTextFormatter.FormatSelectedNodeConfigDraftMissingSelection();
            ShowWorkflowDefinitionNotification(
                "workflow.definition.node_config",
                UiNotificationKind.Error);
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
            ShowWorkflowDefinitionNotification(
                "workflow.definition.node_config",
                UiNotificationKind.Error);
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
            ShowWorkflowDefinitionNotification(
                "workflow.definition.node_config",
                UiNotificationKind.Error);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        WorkflowDefinitionValidationMessage = T("definition.node_config_applied");
        WorkflowDefinitionValidationErrorMessage = null;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.node_config",
            UiNotificationKind.Success);
    }

    [RelayCommand(CanExecute = nameof(CanApplyRuntimeOptionsDraft))]
    private void ApplyRuntimeOptionsDraft()
    {
        if (IsRuntimeOptionsJsonEditorExpanded && IsRuntimeOptionsJsonDraftDirty)
        {
            ApplyRuntimeOptionsJsonDraft();
            return;
        }

        ApplyRuntimeOptionsStructuredDraft();
    }

    [RelayCommand(CanExecute = nameof(CanApplyRuntimeOptionsDraft))]
    private void RegenerateRuntimeOptionsJsonDraft()
    {
        if (!TryBuildRuntimeOptionsDraftFromStructuredInputs(
            out var draft,
            out var errorMessage))
        {
            RuntimeOptionsEditorErrorMessage = errorMessage;
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        SetRuntimeOptionsJsonDraft(
            WorkflowDefinitionDraftRuntimeOptionsPatcher.FormatRuntimeOptions(draft),
            isDirty: false);
        RuntimeOptionsEditorErrorMessage = null;
        OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
    }

    private void ApplyRuntimeOptionsStructuredDraft()
    {
        var readResult = RuntimeOptionsDraftReader.Read(WorkflowDefinitionDraftJson);
        if (!readResult.Succeeded)
        {
            RuntimeOptionsEditorErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(readResult.Warning);
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        if (!TryBuildRuntimeOptionsDraftFromStructuredInputs(
            readResult.Draft,
            out var draft,
            out var errorMessage))
        {
            RuntimeOptionsEditorErrorMessage = errorMessage;
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        ApplyRuntimeOptionsDraftToWorkflow(draft);
    }

    private void ApplyRuntimeOptionsJsonDraft()
    {
        var readResult = RuntimeOptionsDraftReader.ReadRuntimeOptionsJson(
            RuntimeOptionsJsonDraft);
        if (!readResult.Succeeded)
        {
            RuntimeOptionsEditorErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(readResult.Warning);
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        if (!TryValidateRuntimeOptionsDraft(
            readResult.Draft,
            out var errorMessage))
        {
            RuntimeOptionsEditorErrorMessage = errorMessage;
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        if (ApplyRuntimeOptionsDraftToWorkflow(readResult.Draft))
        {
            SetRuntimeOptionsJsonDraft(
                WorkflowDefinitionDraftRuntimeOptionsPatcher.FormatRuntimeOptions(
                    readResult.Draft),
                isDirty: false);
        }
    }

    [RelayCommand(CanExecute = nameof(CanResetRuntimeOptionsSelectedNodeOverride))]
    private void ResetRuntimeOptionsSelectedNodeOverride()
    {
        if (SelectedRuntimeOptionsNode is null)
        {
            return;
        }

        var readResult = RuntimeOptionsDraftReader.Read(WorkflowDefinitionDraftJson);
        if (!readResult.Succeeded)
        {
            RuntimeOptionsEditorErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(readResult.Warning);
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        var nodeOverrides =
            new Dictionary<string, RuntimeOptionsNodeOverrideDraft>(
                readResult.Draft.NodeOverrides);
        nodeOverrides.Remove(SelectedRuntimeOptionsNode.NodeInstanceId);
        var draft = readResult.Draft with
        {
            NodeOverrides = nodeOverrides,
        };
        var patchResult = WorkflowDefinitionDraftRuntimeOptionsPatcher.Apply(
            WorkflowDefinitionDraftJson,
            draft);
        if (!patchResult.Succeeded)
        {
            RuntimeOptionsEditorErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        RefreshSelectedRuntimeOptionsNodeDraftState(draft);
        RuntimeOptionsEditorErrorMessage = null;
        OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
        WorkflowDefinitionValidationMessage =
            T("definition.runtime_options_node_override_reset");
        WorkflowDefinitionValidationErrorMessage = null;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.runtime_options",
            UiNotificationKind.Success);
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
            ShowWorkflowDefinitionNotification(
                "workflow.definition.node_display_name",
                UiNotificationKind.Error);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        SelectWorkflowDefinitionDraftNode(nodeInstanceId);
        WorkflowDefinitionValidationMessage = T("definition.node_display_name_applied");
        WorkflowDefinitionValidationErrorMessage = null;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.node_display_name",
            UiNotificationKind.Success);
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
            ShowWorkflowDefinitionNotification(
                "workflow.definition.add_node",
                UiNotificationKind.Error);
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
            autoWirePorts.OutputPort,
            autoWirePorts.SourceOutputPort);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_add_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            ShowWorkflowDefinitionNotification(
                "workflow.definition.add_node",
                UiNotificationKind.Error);
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
        ShowWorkflowDefinitionNotification(
            "workflow.definition.add_node",
            UiNotificationKind.Success);
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

        var patchResult = WorkflowDefinitionDraftNodePatcher.DeleteNodeWithLinearBridge(
            WorkflowDefinitionDraftJson,
            SelectedWorkflowDefinitionNode.NodeInstanceId);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_delete_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            ShowWorkflowDefinitionNotification(
                "workflow.definition.delete_node",
                UiNotificationKind.Error);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        WorkflowDefinitionValidationMessage =
            patchResult.AddedConnections.Count > 0
                ? T("definition.node_deleted_with_rewired_connections")
                : patchResult.RemovedConnections.Count > 0
                ? T("definition.node_deleted_with_connections")
                : T("definition.node_deleted");
        WorkflowDefinitionValidationErrorMessage =
            patchResult.AddedConnections.Count > 0
                ? FormatDeletedRewiredConnectionsMessage(
                    patchResult.RemovedConnections,
                    patchResult.AddedConnections)
                : FormatRemovedConnectionsMessage(patchResult.RemovedConnections);
        ShowWorkflowDefinitionNotification(
            "workflow.definition.delete_node",
            UiNotificationKind.Success);
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
            ShowWorkflowDefinitionNotification(
                "workflow.definition.delete_nodes",
                UiNotificationKind.Error);
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
        ShowWorkflowDefinitionNotification(
            "workflow.definition.delete_nodes",
            UiNotificationKind.Success);
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
            ShowWorkflowDefinitionNotification(
                "workflow.definition.copy_node",
                UiNotificationKind.Error);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        if (!string.IsNullOrWhiteSpace(patchResult.AddedNodeInstanceId))
        {
            SelectWorkflowDefinitionDraftNode(patchResult.AddedNodeInstanceId);
        }

        WorkflowDefinitionValidationMessage = T("definition.node_copied");
        WorkflowDefinitionValidationErrorMessage = null;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.copy_node",
            UiNotificationKind.Success);
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
        var patchResult = WorkflowDefinitionDraftNodePatcher.MoveNodeWithLinearRewire(
            WorkflowDefinitionDraftJson,
            nodeInstanceId,
            offset);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_move_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            ShowWorkflowDefinitionNotification(
                "workflow.definition.move_node",
                UiNotificationKind.Error);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        SelectWorkflowDefinitionDraftNode(nodeInstanceId);
        WorkflowDefinitionValidationMessage =
            patchResult.AddedConnections.Count > 0
                ? T("definition.node_moved_with_rewired_connections")
                : T("definition.node_moved");
        WorkflowDefinitionValidationErrorMessage =
            patchResult.AddedConnections.Count > 0
                ? FormatMovedRewiredConnectionsMessage(
                    patchResult.RemovedConnections,
                    patchResult.AddedConnections)
                : null;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.move_node",
            UiNotificationKind.Success);
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
        await TrySaveWorkflowDefinitionDraftAsync();
    }

    private async Task<bool> TrySaveWorkflowDefinitionDraftAsync()
    {
        if (WorkflowDefinitionDetail is null)
        {
            WorkflowDefinitionValidationMessage = T("definition.save_rejected");
            WorkflowDefinitionValidationErrorMessage = T("definition.load_before_saving");
            ShowWorkflowDefinitionNotification(
                "workflow.definition.save",
                UiNotificationKind.Error);
            return false;
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
            ShowWorkflowDefinitionNotification(
                "workflow.definition.save",
                UiNotificationKind.Error);
            return false;
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
                ShowWorkflowDefinitionNotification(
                    "workflow.definition.save",
                    UiNotificationKind.Success);
                IsWorkflowDefinitionDraftDirty = false;
                HasWorkflowDefinitionRevisionConflict = false;
                await RefreshWorkflowsSelectingAsync(saved.Data.WorkflowId);
                await LoadSelectedWorkflowDefinitionAsync();
                return true;
            }

            if (saved.Error?.ErrorCode == "WORKFLOW_REVISION_CONFLICT")
            {
                HasWorkflowDefinitionRevisionConflict = true;
                WorkflowDefinitionValidationMessage = T("definition.save_failed");
                WorkflowDefinitionValidationErrorMessage = T("definition.revision_conflict");
                ShowWorkflowDefinitionNotification(
                    "workflow.definition.save",
                    UiNotificationKind.Error);
                return false;
            }

            WorkflowDefinitionValidationMessage = T("definition.save_failed");
            WorkflowDefinitionValidationErrorMessage = DescribeError(saved);
            ShowWorkflowDefinitionNotification(
                "workflow.definition.save",
                UiNotificationKind.Error);
            return false;
        }
        finally
        {
            IsSavingWorkflowDefinitionDraft = false;
        }
    }

    private async Task<bool> EnsureWorkflowDefinitionDraftSavedForRunAsync()
    {
        return !IsWorkflowDefinitionDraftDirty ||
            await TrySaveWorkflowDefinitionDraftAsync();
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
                var previousSelectedTableRefId = SelectedDataPreviewTableRef?.TableRefId;
                var previousSelectedStateKey = SelectedDataPreviewState?.StateKey;
                var previousSelectedTableOptionId =
                    SelectedDataPreviewTableOption?.TableRefId ?? previousSelectedTableRefId;
                TableRefs.Clear();
                foreach (var tableRef in response.Data)
                {
                    TableRefs.Add(new TableRefListItemViewModel(tableRef));
                }

                RebuildDataPreviewStates(
                    previousSelectedStateKey,
                    previousSelectedTableOptionId);
                SelectedDataPreviewTableRef = TableRefs.FirstOrDefault(
                    tableRef => tableRef.TableRefId == previousSelectedTableRefId)
                    ?? SelectedDataPreviewTableOption
                    ?? TableRefs.FirstOrDefault();

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

    [RelayCommand(CanExecute = nameof(CanLoadSelectedDataPreviewTable))]
    private async Task LoadSelectedDataPreviewTableAsync()
    {
        await LoadDataPreviewWorkbenchTablePageAsync(SelectedDataPreviewTableOption, 0);
    }

    [RelayCommand(CanExecute = nameof(CanLoadPreviousDataPreviewWorkbenchPage))]
    private async Task LoadPreviousDataPreviewWorkbenchPageAsync()
    {
        await LoadDataPreviewWorkbenchTablePageAsync(
            LoadedDataPreviewTableRef,
            Math.Max(0, dataPreviewWorkbenchOffset - DataPreviewRowLimit));
    }

    [RelayCommand(CanExecute = nameof(CanLoadNextDataPreviewWorkbenchPage))]
    private async Task LoadNextDataPreviewWorkbenchPageAsync()
    {
        await LoadDataPreviewWorkbenchTablePageAsync(
            LoadedDataPreviewTableRef,
            dataPreviewWorkbenchOffset + DataPreviewRowLimit);
    }

    [RelayCommand(CanExecute = nameof(CanCopyDataPreviewWorkbenchTsv))]
    private void CopyDataPreviewWorkbenchTsv()
    {
        DataPreviewWorkbenchClipboardText = BuildDataPreviewWorkbenchTsv();
    }

    [RelayCommand(CanExecute = nameof(CanParseDataPreviewWorkbenchPaste))]
    private void ParseDataPreviewWorkbenchPaste()
    {
        DataPreviewWorkbenchErrorMessage = null;
        if (!TryParseDelimitedTable(
                DataPreviewWorkbenchPasteText,
                out var columns,
                out var rows,
                out var errorKey))
        {
            DataPreviewWorkbenchMessage = T("data_preview.workbench_parse_failed");
            DataPreviewWorkbenchErrorMessage = errorKey is null ? null : T(errorKey);
            return;
        }

        LoadedDataPreviewTableRef = null;
        LoadDataPreviewWorkbenchRows(
            new TableDataRowsDto
            {
                TableRefId = "local-draft",
                Offset = 0,
                Limit = rows.Length,
                RowCount = rows.Length,
                Columns = columns,
                Rows = rows,
                HasMore = false,
            },
            isDraft: true);
        DataPreviewWorkbenchMessage = F(
            "format.data_preview_imported_rows",
            rows.Length,
            columns.Length);
    }

    [RelayCommand(CanExecute = nameof(CanRestoreDataPreviewWorkbenchDraft))]
    private void RestoreDataPreviewWorkbenchDraft()
    {
        dataPreviewWorkbenchEditableCellRows = CloneCellRows(dataPreviewWorkbenchOriginalCellRows);
        ApplyDataPreviewWorkbenchSearch();
        NotifyDataPreviewWorkbenchDirtyStateChanged();
        DataPreviewWorkbenchClipboardText = string.Empty;
        DataPreviewWorkbenchMessage = T("data_preview.draft_restored");
    }

    [RelayCommand(CanExecute = nameof(CanSaveDataPreviewWorkbenchAs))]
    private void SaveDataPreviewWorkbenchAs()
    {
        DataPreviewWorkbenchMessage = T("data_preview.save_as_api_pending");
        DataPreviewWorkbenchErrorMessage = null;
    }

    private async Task LoadDataPreviewWorkbenchTablePageAsync(
        TableRefListItemViewModel? requestedTableRef,
        int offset)
    {
        if (requestedTableRef is null)
        {
            return;
        }

        var requestedTableRefId = requestedTableRef.TableRefId;
        var requestVersion = ++dataPreviewWorkbenchLoadVersion;
        IsLoadingDataPreviewWorkbench = true;
        DataPreviewWorkbenchMessage = F(
            "format.loading_data_preview_table",
            requestedTableRef.LogicalTableId);
        DataPreviewWorkbenchErrorMessage = null;

        try
        {
            var response = await _apiClient.GetTableDataRowsAsync(
                BuildSettings(),
                requestedTableRefId,
                offset: Math.Max(0, offset),
                limit: DataPreviewRowLimit,
                cancellationToken: _shutdown.Token);

            if (IsStaleDataPreviewWorkbenchRequest(requestVersion))
            {
                return;
            }

            if (!response.Ok || response.Data is null)
            {
                DataPreviewWorkbenchMessage = T("data_preview.workbench_load_failed");
                DataPreviewWorkbenchErrorMessage = DescribeError(response);
                return;
            }

            LoadDataPreviewWorkbenchRows(response.Data);
            LoadedDataPreviewTableRef = requestedTableRef;
            UpdateDataPreviewWorkbenchLoadedMessage();
        }
        finally
        {
            if (requestVersion == dataPreviewWorkbenchLoadVersion)
            {
                IsLoadingDataPreviewWorkbench = false;
            }
        }
    }

    [RelayCommand(CanExecute = nameof(CanShowDataPreviewDetails))]
    private async Task ShowDataPreviewDetailsAsync()
    {
        var tableRefId = dataPreviewSourceTableRefId;
        var workflowRunId = dataPreviewSourceWorkflowRunId;
        if (string.IsNullOrWhiteSpace(tableRefId) || string.IsNullOrWhiteSpace(workflowRunId))
        {
            return;
        }

        var target = TableRefs.FirstOrDefault(
            tableRef => string.Equals(tableRef.TableRefId, tableRefId, StringComparison.Ordinal));
        if (target is null)
        {
            var response = await _apiClient.ListTableRefsAsync(
                BuildSettings(),
                workflowRunId,
                _shutdown.Token);
            if (response.Ok && response.Data is not null)
            {
                TableRefs.Clear();
                foreach (var tableRef in response.Data)
                {
                    TableRefs.Add(new TableRefListItemViewModel(tableRef));
                }

                RebuildDataPreviewStates(preferredTableRefId: tableRefId);
                TableRefMessage = F("format.loaded_table_refs", TableRefs.Count);
                TableRefErrorMessage = null;
                target = TableRefs.FirstOrDefault(
                    tableRef => string.Equals(tableRef.TableRefId, tableRefId, StringComparison.Ordinal));
            }
            else
            {
                DataPreviewWorkbenchMessage = T("data_preview.workbench_load_failed");
                DataPreviewWorkbenchErrorMessage = DescribeError(response);
                return;
            }
        }

        if (target is null)
        {
            DataPreviewWorkbenchMessage = T("data_preview.workbench_table_not_found");
            DataPreviewWorkbenchErrorMessage = null;
            return;
        }

        SelectDataPreviewTableOptionByTableRefId(target.TableRefId);
        SelectedDataPreviewTableRef = target;
        SelectedShellPageKey = ShellPageKey.DataPreview;
        await LoadSelectedDataPreviewTableAsync();
    }

    private async Task<bool> TryRefreshSelectedWorkflowNodeDataPreviewAsync(
        bool notifyResult = true)
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
                if (notifyResult)
                {
                    ShowDataPreviewNotification(UiNotificationKind.Error);
                }

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
                if (notifyResult)
                {
                    ShowDataPreviewNotification(UiNotificationKind.Warning);
                }

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
                if (notifyResult)
                {
                    ShowDataPreviewNotification(UiNotificationKind.Error);
                }

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
                if (notifyResult)
                {
                    ShowDataPreviewNotification(UiNotificationKind.Warning);
                }

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
                if (notifyResult)
                {
                    ShowDataPreviewNotification(UiNotificationKind.Error);
                }

                return false;
            }

            LoadDataPreviewRows(rowsResponse.Data);
            UpdateDataPreviewSource(
                requestedRunId,
                requestedNodeInstanceId,
                tableRef.LogicalTableId,
                tableRef.TableRefId,
                SelectedRun?.RunMode,
                SelectedRun?.TargetNodeInstanceId);
            DataPreviewMessage = F(
                "format.loaded_data_preview",
                rowsResponse.Data.Rows.Length,
                rowsResponse.Data.RowCount,
                tableRef.LogicalTableId);
            if (notifyResult)
            {
                ShowDataPreviewNotification(UiNotificationKind.Success);
            }

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
                loadedCurrentPreview = await TryRefreshSelectedWorkflowNodeDataPreviewAsync(
                    notifyResult: false);
            }

            if (loadedCurrentPreview)
            {
                ShowDataPreviewNotification(UiNotificationKind.Success);
                return;
            }

            if (SelectedRun is not null && IsTerminalRunStatus(SelectedRun.Status))
            {
                ShowDataPreviewNotification(
                    HasDataPreviewError ? UiNotificationKind.Error : UiNotificationKind.Warning);
                return;
            }

            if (attempt + 1 < DataPreviewRunRefreshAttemptCount)
            {
                await _dataPreviewRunRefreshDelay(_shutdown.Token);
            }
        }

        ShowDataPreviewNotification(
            HasDataPreviewError ? UiNotificationKind.Error : UiNotificationKind.Warning);
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

    private bool IsStaleDataPreviewWorkbenchRequest(int requestVersion)
    {
        return requestVersion != dataPreviewWorkbenchLoadVersion;
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

    private void RebuildDataPreviewStates(
        string? preferredStateKey = null,
        string? preferredTableRefId = null)
    {
        DataPreviewStates.Clear();
        foreach (var state in DataPreviewStateListItemViewModel.FromTableRefs(TableRefs))
        {
            DataPreviewStates.Add(state);
        }

        var selectedState =
            FindDataPreviewStateByKey(preferredStateKey)
            ?? FindDataPreviewStateByTableRefId(preferredTableRefId)
            ?? DataPreviewStates.FirstOrDefault();
        SelectedDataPreviewState = selectedState;

        if (!string.IsNullOrWhiteSpace(preferredTableRefId))
        {
            SelectedDataPreviewTableOption =
                DataPreviewTableOptions.FirstOrDefault(tableRef =>
                    string.Equals(tableRef.TableRefId, preferredTableRefId, StringComparison.Ordinal))
                ?? SelectedDataPreviewTableOption;
        }
    }

    private DataPreviewStateListItemViewModel? FindDataPreviewStateByKey(string? stateKey)
    {
        return string.IsNullOrWhiteSpace(stateKey)
            ? null
            : DataPreviewStates.FirstOrDefault(state =>
                string.Equals(state.StateKey, stateKey, StringComparison.Ordinal));
    }

    private DataPreviewStateListItemViewModel? FindDataPreviewStateByTableRefId(string? tableRefId)
    {
        return string.IsNullOrWhiteSpace(tableRefId)
            ? null
            : DataPreviewStates.FirstOrDefault(state =>
                state.TableRefs.Any(tableRef =>
                    string.Equals(tableRef.TableRefId, tableRefId, StringComparison.Ordinal)));
    }

    private void SelectDataPreviewTableOptionByTableRefId(string? tableRefId)
    {
        var state = FindDataPreviewStateByTableRefId(tableRefId);
        if (state is null)
        {
            return;
        }

        SelectedDataPreviewState = state;
        SelectedDataPreviewTableOption =
            DataPreviewTableOptions.FirstOrDefault(tableRef =>
                string.Equals(tableRef.TableRefId, tableRefId, StringComparison.Ordinal))
            ?? SelectedDataPreviewTableOption;
    }

    private void ResetDataPreviewSelectionState()
    {
        dataPreviewLoadVersion++;
        IsLoadingDataPreview = false;
        DataPreviewMessage = T("status.select_run_and_workflow_node_data_preview");
        DataPreviewErrorMessage = null;
        ClearDataPreviewSourceIfNoPreviewRows();
        RefreshSelectedWorkflowNodeDataPreviewCommand.NotifyCanExecuteChanged();
        ShowDataPreviewDetailsCommand.NotifyCanExecuteChanged();
    }

    private void ClearDataPreviewSourceIfNoPreviewRows()
    {
        if (HasDataPreviewColumns || HasDataPreviewRows)
        {
            return;
        }

        dataPreviewSourceWorkflowRunId = null;
        dataPreviewSourceNodeInstanceId = null;
        dataPreviewSourceLogicalTableId = null;
        dataPreviewSourceTableRefId = null;
        dataPreviewSourceRunMode = null;
        dataPreviewSourceTargetNodeInstanceId = null;
        OnPropertyChanged(nameof(DataPreviewSourceText));
    }

    private void ResetDataPreviewWorkbenchState()
    {
        dataPreviewWorkbenchLoadVersion++;
        IsLoadingDataPreviewWorkbench = false;
        SelectedDataPreviewState = null;
        DataPreviewStates.Clear();
        SelectedDataPreviewTableOption = null;
        DataPreviewTableOptions.Clear();
        SelectedDataPreviewTableRef = null;
        ResetDataPreviewWorkbenchLoadedState();
        DataPreviewWorkbenchColumns.Clear();
        DataPreviewWorkbenchRows.Clear();
        DataPreviewWorkbenchMessage = T("data_preview.workbench_select_table");
        DataPreviewWorkbenchErrorMessage = null;
        NotifyDataPreviewWorkbenchRowsChanged();
        LoadSelectedDataPreviewTableCommand.NotifyCanExecuteChanged();
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

    private void LoadDataPreviewWorkbenchRows(TableDataRowsDto rows, bool isDraft = false)
    {
        IsDataPreviewWorkbenchDraft = isDraft;
        dataPreviewWorkbenchLoadedColumns = rows.Columns.ToArray();
        dataPreviewWorkbenchLoadedRows = rows.Rows.Select(row => row.Clone()).ToArray();
        dataPreviewWorkbenchOriginalCellRows = dataPreviewWorkbenchLoadedRows
            .Select(row => CreateCellRow(row, dataPreviewWorkbenchLoadedColumns))
            .ToArray();
        dataPreviewWorkbenchEditableCellRows = CloneCellRows(dataPreviewWorkbenchOriginalCellRows);
        dataPreviewWorkbenchOffset = rows.Offset;
        dataPreviewWorkbenchHasMore = rows.HasMore;
        dataPreviewWorkbenchRowCount = rows.RowCount;
        DataPreviewWorkbenchClipboardText = string.Empty;
        ApplyDataPreviewWorkbenchSearch();
        NotifyDataPreviewWorkbenchPagingChanged();
        NotifyDataPreviewWorkbenchDirtyStateChanged();
        OnPropertyChanged(nameof(DataPreviewWorkbenchSourceText));
    }

    private void ResetDataPreviewWorkbenchLoadedState()
    {
        LoadedDataPreviewTableRef = null;
        dataPreviewWorkbenchLoadedColumns = [];
        dataPreviewWorkbenchLoadedRows = [];
        dataPreviewWorkbenchOriginalCellRows = [];
        dataPreviewWorkbenchEditableCellRows = [];
        dataPreviewWorkbenchOffset = 0;
        dataPreviewWorkbenchHasMore = false;
        dataPreviewWorkbenchRowCount = 0;
        DataPreviewWorkbenchClipboardText = string.Empty;
        IsDataPreviewWorkbenchDraft = false;
        NotifyDataPreviewWorkbenchPagingChanged();
        NotifyDataPreviewWorkbenchDirtyStateChanged();
    }

    private void ApplyDataPreviewWorkbenchSearch()
    {
        var filter = NormalizeFilter(DataPreviewWorkbenchSearchText);
        var visibleRowIndexes = Enumerable.Range(0, dataPreviewWorkbenchEditableCellRows.Length);
        if (filter is not null)
        {
            visibleRowIndexes = visibleRowIndexes
                .Where(rowIndex => DataPreviewWorkbenchRowMatches(rowIndex, filter))
                .ToArray();
        }

        DataPreviewWorkbenchColumns.Clear();
        foreach (var column in dataPreviewWorkbenchLoadedColumns)
        {
            DataPreviewWorkbenchColumns.Add(new TableDataPreviewColumnViewModel(column));
        }

        DataPreviewWorkbenchRows.Clear();
        foreach (var rowIndex in visibleRowIndexes)
        {
            DataPreviewWorkbenchRows.Add(CreateDataPreviewWorkbenchRow(rowIndex));
        }

        NotifyDataPreviewWorkbenchRowsChanged();
    }

    private TableDataPreviewRowViewModel CreateDataPreviewWorkbenchRow(int rowIndex)
    {
        return new TableDataPreviewRowViewModel(
            dataPreviewWorkbenchEditableCellRows[rowIndex]
                .Select(
                    (value, columnIndex) =>
                        new TableDataPreviewCellViewModel(
                            value,
                            updatedValue => UpdateDataPreviewWorkbenchCell(
                                rowIndex,
                                columnIndex,
                                updatedValue)))
                .ToArray());
    }

    private bool DataPreviewWorkbenchRowMatches(int rowIndex, string filter)
    {
        return dataPreviewWorkbenchEditableCellRows[rowIndex].Any(
            value => value.Contains(
                filter,
                StringComparison.OrdinalIgnoreCase));
    }

    private static string[] CreateCellRow(JsonElement row, string[] columns)
    {
        return columns.Select(column => FormatDataPreviewCell(row, column)).ToArray();
    }

    private static string[][] CloneCellRows(string[][] rows)
    {
        return rows.Select(row => row.ToArray()).ToArray();
    }

    private void UpdateDataPreviewWorkbenchCell(
        int rowIndex,
        int columnIndex,
        string value)
    {
        if (rowIndex < 0
            || rowIndex >= dataPreviewWorkbenchEditableCellRows.Length
            || columnIndex < 0
            || columnIndex >= dataPreviewWorkbenchEditableCellRows[rowIndex].Length)
        {
            return;
        }

        if (string.Equals(
                dataPreviewWorkbenchEditableCellRows[rowIndex][columnIndex],
                value,
                StringComparison.Ordinal))
        {
            return;
        }

        dataPreviewWorkbenchEditableCellRows[rowIndex][columnIndex] = value;
        DataPreviewWorkbenchClipboardText = string.Empty;
        NotifyDataPreviewWorkbenchDirtyStateChanged();
    }

    private static bool DataPreviewWorkbenchCellRowsEqual(string[][] left, string[][] right)
    {
        if (left.Length != right.Length)
        {
            return false;
        }

        for (var rowIndex = 0; rowIndex < left.Length; rowIndex++)
        {
            if (!left[rowIndex].SequenceEqual(right[rowIndex], StringComparer.Ordinal))
            {
                return false;
            }
        }

        return true;
    }

    private string BuildDataPreviewWorkbenchTsv()
    {
        var builder = new StringBuilder();
        builder.AppendLine(string.Join("\t", DataPreviewWorkbenchColumns.Select(column => EscapeTsv(column.Name))));
        foreach (var row in DataPreviewWorkbenchRows)
        {
            builder.AppendLine(string.Join("\t", row.Cells.Select(cell => EscapeTsv(cell.Text))));
        }

        return builder.ToString().TrimEnd('\r', '\n');
    }

    private static string EscapeTsv(string value)
    {
        return value
            .Replace("\r\n", " ", StringComparison.Ordinal)
            .Replace("\r", " ", StringComparison.Ordinal)
            .Replace("\n", " ", StringComparison.Ordinal)
            .Replace('\t', ' ');
    }

    private static bool TryParseDelimitedTable(
        string text,
        out string[] columns,
        out JsonElement[] rows,
        out string? errorMessage)
    {
        columns = [];
        rows = [];
        errorMessage = null;

        var lines = text
            .Replace("\r\n", "\n", StringComparison.Ordinal)
            .Replace('\r', '\n')
            .Split('\n')
            .Where(line => !string.IsNullOrWhiteSpace(line))
            .ToArray();
        if (lines.Length < 2)
        {
            errorMessage = "data_preview.paste_requires_rows";
            return false;
        }

        var delimiter = lines[0].Contains('\t', StringComparison.Ordinal) ? '\t' : ',';
        var parsedRows = lines.Select(line => ParseDelimitedLine(line, delimiter)).ToArray();
        var maxColumnCount = parsedRows.Max(row => row.Length);
        if (maxColumnCount == 0)
        {
            errorMessage = "data_preview.paste_no_columns";
            return false;
        }

        var parsedColumns = NormalizeDelimitedHeaders(parsedRows[0], maxColumnCount);
        var parsedDataRows = parsedRows
            .Skip(1)
            .Select(row => CreateDelimitedRowElement(parsedColumns, row))
            .ToArray();
        columns = parsedColumns;
        rows = parsedDataRows;
        if (rows.Length == 0)
        {
            errorMessage = "data_preview.paste_no_rows";
            return false;
        }

        return true;
    }

    private static string[] ParseDelimitedLine(string line, char delimiter)
    {
        var values = new List<string>();
        var current = new StringBuilder();
        var inQuotes = false;

        for (var index = 0; index < line.Length; index++)
        {
            var character = line[index];
            if (character == '"')
            {
                if (inQuotes && index + 1 < line.Length && line[index + 1] == '"')
                {
                    current.Append('"');
                    index++;
                    continue;
                }

                inQuotes = !inQuotes;
                continue;
            }

            if (!inQuotes && character == delimiter)
            {
                values.Add(current.ToString());
                current.Clear();
                continue;
            }

            current.Append(character);
        }

        values.Add(current.ToString());
        return values.ToArray();
    }

    private static string[] NormalizeDelimitedHeaders(string[] headerRow, int columnCount)
    {
        var headers = new string[columnCount];
        var seen = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        for (var index = 0; index < columnCount; index++)
        {
            var header = index < headerRow.Length ? headerRow[index].Trim() : string.Empty;
            if (string.IsNullOrWhiteSpace(header))
            {
                header = $"Column{index + 1}";
            }

            if (seen.TryGetValue(header, out var count))
            {
                count++;
                seen[header] = count;
                header = $"{header}_{count}";
            }
            else
            {
                seen[header] = 1;
            }

            headers[index] = header;
        }

        return headers;
    }

    private static JsonElement CreateDelimitedRowElement(string[] columns, string[] values)
    {
        var row = new Dictionary<string, string>(StringComparer.Ordinal);
        for (var index = 0; index < columns.Length; index++)
        {
            row[columns[index]] = index < values.Length ? values[index] : string.Empty;
        }

        return JsonSerializer.SerializeToElement(row, FlowWeaverJson.Options).Clone();
    }

    private void UpdateDataPreviewWorkbenchLoadedMessage()
    {
        if (LoadedDataPreviewTableRef is null)
        {
            return;
        }

        var filter = NormalizeFilter(DataPreviewWorkbenchSearchText);
        DataPreviewWorkbenchMessage = filter is null
            ? F(
                "format.loaded_data_preview_table_rows",
                dataPreviewWorkbenchLoadedRows.Length,
                dataPreviewWorkbenchRowCount,
                LoadedDataPreviewTableRef.LogicalTableId)
            : F(
                "format.data_preview_search_matches",
                DataPreviewWorkbenchRows.Count,
                dataPreviewWorkbenchLoadedRows.Length,
                filter);
    }

    private void UpdateDataPreviewSource(
        string workflowRunId,
        string nodeInstanceId,
        string logicalTableId,
        string tableRefId,
        string? runMode,
        string? targetNodeInstanceId)
    {
        dataPreviewSourceWorkflowRunId = workflowRunId;
        dataPreviewSourceNodeInstanceId = nodeInstanceId;
        dataPreviewSourceLogicalTableId = logicalTableId;
        dataPreviewSourceTableRefId = tableRefId;
        dataPreviewSourceRunMode = runMode;
        dataPreviewSourceTargetNodeInstanceId = targetNodeInstanceId;
        OnPropertyChanged(nameof(DataPreviewSourceText));
        ShowDataPreviewDetailsCommand.NotifyCanExecuteChanged();
    }

    private string FormatDataPreviewSourceText()
    {
        if (string.Equals(
                dataPreviewSourceRunMode,
                "preview_to_node",
                StringComparison.OrdinalIgnoreCase))
        {
            return F(
                "format.data_preview_source_preview",
                dataPreviewSourceWorkflowRunId!,
                string.IsNullOrWhiteSpace(dataPreviewSourceTargetNodeInstanceId)
                    ? dataPreviewSourceNodeInstanceId!
                    : dataPreviewSourceTargetNodeInstanceId!,
                dataPreviewSourceLogicalTableId!);
        }

        return F(
            "format.data_preview_source_full",
            dataPreviewSourceWorkflowRunId!,
            dataPreviewSourceNodeInstanceId!,
            dataPreviewSourceLogicalTableId!);
    }

    private void NotifyDataPreviewRowsChanged()
    {
        OnPropertyChanged(nameof(HasDataPreviewColumns));
        OnPropertyChanged(nameof(HasDataPreviewRows));
    }

    private void NotifyDataPreviewWorkbenchRowsChanged()
    {
        OnPropertyChanged(nameof(HasDataPreviewWorkbenchColumns));
        OnPropertyChanged(nameof(HasDataPreviewWorkbenchRows));
        OnPropertyChanged(nameof(DataPreviewWorkbenchPageText));
        CopyDataPreviewWorkbenchTsvCommand.NotifyCanExecuteChanged();
    }

    private void NotifyDataPreviewWorkbenchPagingChanged()
    {
        OnPropertyChanged(nameof(DataPreviewWorkbenchPageText));
        LoadPreviousDataPreviewWorkbenchPageCommand.NotifyCanExecuteChanged();
        LoadNextDataPreviewWorkbenchPageCommand.NotifyCanExecuteChanged();
    }

    private void NotifyDataPreviewWorkbenchDirtyStateChanged()
    {
        OnPropertyChanged(nameof(IsDataPreviewWorkbenchDirty));
        OnPropertyChanged(nameof(DataPreviewWorkbenchDirtyStateText));
        OnPropertyChanged(nameof(CanSaveDataPreviewWorkbenchAsDraft));
        OnPropertyChanged(nameof(DataPreviewWorkbenchSavePolicyText));
        RestoreDataPreviewWorkbenchDraftCommand.NotifyCanExecuteChanged();
        SaveDataPreviewWorkbenchAsCommand.NotifyCanExecuteChanged();
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

    private void RefreshNodeEditorSchemaFallbackNodes()
    {
        _nodeEditorResolver.ReplaceSchemaFallbackNodes(
            NodeDefinitions
                .Where(definition => definition.ConfigSchemaDescriptor?.IsSupported == true)
                .Select(definition => (
                    definition.NodeType,
                    string.IsNullOrWhiteSpace(definition.DisplayName)
                        ? definition.NodeType
                        : definition.DisplayName)));
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
            var displayOrder = 1;
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
                    _nodeEditorResolver.Resolve(node.NodeType, node.DisplayName),
                    displayOrder)
                {
                    IsBatchSelected = batchSelectedNodeIds.Contains(node.NodeInstanceId),
                };
                nodeItem.PropertyChanged += OnWorkflowDefinitionDraftNodeItemPropertyChanged;
                WorkflowDefinitionDraftNodes.Add(nodeItem);
                displayOrder++;
            }
        }

        SelectedWorkflowDefinitionNode = WorkflowDefinitionDraftNodes.FirstOrDefault(node =>
            string.Equals(node.NodeInstanceId, selectedNodeId, StringComparison.Ordinal));
        if (SelectedWorkflowDefinitionNode is null && !hadSelectedNode)
        {
            SelectedWorkflowDefinitionNode = WorkflowDefinitionDraftNodes.FirstOrDefault();
        }

        OnPropertyChanged(nameof(WorkflowDefinitionDraftNodeCountText));
        OnPropertyChanged(nameof(WorkflowLinearChainStatusText));
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
        OnPropertyChanged(nameof(DeleteSelectedWorkflowDefinitionDraftNodesDisabledReasonText));
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

    private void RefreshRuntimeOptionsDraftState()
    {
        var readResult = string.IsNullOrWhiteSpace(WorkflowDefinitionDraftJson)
            ? new RuntimeOptionsDraftReadResult
            {
                Status = RuntimeOptionsDraftReadStatus.Succeeded,
                Draft = new RuntimeOptionsDraft(),
            }
            : RuntimeOptionsDraftReader.Read(WorkflowDefinitionDraftJson);
        var draft = readResult.Succeeded ? readResult.Draft : new RuntimeOptionsDraft();

        RuntimeOptionsProfileDraft = draft.Workflow.Profile;
        RuntimeOptionsStrictValidationDraft = draft.Workflow.StrictValidation;
        RuntimeOptionsLogLevelDraft = draft.Workflow.Telemetry.LogLevel;
        RuntimeOptionsEventLevelDraft = draft.Workflow.Telemetry.EventLevel;
        RuntimeOptionsEventRateLimitPerSecondDraft =
            FormatInvariant(draft.Workflow.Telemetry.EventRateLimitPerSecond);
        RuntimeOptionsProgressEnabledDraft = draft.Workflow.Telemetry.ProgressEnabled;
        RuntimeOptionsProgressIntervalSecondsDraft =
            FormatInvariant(draft.Workflow.Telemetry.ProgressIntervalSeconds);
        RuntimeOptionsCaptureErrorContextDraft =
            draft.Workflow.Diagnostics.CaptureErrorContext;
        RuntimeOptionsIncludeMetricsDraft = draft.Workflow.Diagnostics.IncludeMetrics;
        RuntimeOptionsPayloadByteLimitDraft =
            FormatInvariant(draft.Workflow.Diagnostics.PayloadByteLimit);
        RuntimeOptionsTtlSecondsDraft =
            FormatInvariant(draft.Workflow.Diagnostics.TtlSeconds);
        RuntimeOptionsRedactColumnsDraft =
            FormatRuntimeOptionsRedactColumns(draft.Workflow.Diagnostics.RedactColumns);
        RuntimeOptionsMaskPolicyDraft = draft.Workflow.Diagnostics.MaskPolicy;
        RuntimeOptionsNodeOverrideCount = draft.NodeOverrides.Count;
        RuntimeOptionsEditorErrorMessage =
            readResult.Succeeded
                ? null
                : LocalizeWorkflowDefinitionDraftWarning(readResult.Warning);

        if (SelectedRuntimeOptionsNode is not null &&
            !WorkflowDefinitionDraftNodes.Contains(SelectedRuntimeOptionsNode))
        {
            SelectedRuntimeOptionsNode = null;
        }

        RefreshSelectedRuntimeOptionsNodeDraftState(draft);
        NotifyRuntimeOptionsSummaryChanged();
        OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
    }

    private void RefreshSelectedRuntimeOptionsNodeDraftState(
        RuntimeOptionsDraft? currentDraft = null)
    {
        var draft = currentDraft;
        if (draft is null)
        {
            var readResult = RuntimeOptionsDraftReader.Read(WorkflowDefinitionDraftJson);
            draft = readResult.Succeeded ? readResult.Draft : new RuntimeOptionsDraft();
        }

        RuntimeOptionsNodeOverrideDraft? nodeOverride = null;
        if (SelectedRuntimeOptionsNode is not null)
        {
            draft.NodeOverrides.TryGetValue(
                SelectedRuntimeOptionsNode.NodeInstanceId,
                out nodeOverride);
        }

        RuntimeOptionsSelectedNodeProfileDraft =
            nodeOverride?.Profile ?? draft.Workflow.Profile;
        RuntimeOptionsSelectedNodeStrictValidationDraft =
            nodeOverride?.StrictValidation ?? draft.Workflow.StrictValidation;
        RuntimeOptionsSelectedNodeLogLevelDraft =
            nodeOverride?.Telemetry?.LogLevel ?? draft.Workflow.Telemetry.LogLevel;
        RuntimeOptionsSelectedNodeEventLevelDraft =
            nodeOverride?.Telemetry?.EventLevel ?? draft.Workflow.Telemetry.EventLevel;
        RuntimeOptionsSelectedNodeEventRateLimitPerSecondDraft =
            FormatInvariant(
                nodeOverride?.Telemetry?.EventRateLimitPerSecond
                    ?? draft.Workflow.Telemetry.EventRateLimitPerSecond);
        RuntimeOptionsSelectedNodeProgressEnabledDraft =
            nodeOverride?.Telemetry?.ProgressEnabled
            ?? draft.Workflow.Telemetry.ProgressEnabled;
        RuntimeOptionsSelectedNodeProgressIntervalSecondsDraft =
            FormatInvariant(
                nodeOverride?.Telemetry?.ProgressIntervalSeconds
                    ?? draft.Workflow.Telemetry.ProgressIntervalSeconds);
        RuntimeOptionsSelectedNodeCaptureErrorContextDraft =
            nodeOverride?.Diagnostics?.CaptureErrorContext
            ?? draft.Workflow.Diagnostics.CaptureErrorContext;
        RuntimeOptionsSelectedNodeIncludeMetricsDraft =
            nodeOverride?.Diagnostics?.IncludeMetrics
            ?? draft.Workflow.Diagnostics.IncludeMetrics;
        RuntimeOptionsSelectedNodePayloadByteLimitDraft =
            FormatInvariant(
                nodeOverride?.Diagnostics?.PayloadByteLimit
                    ?? draft.Workflow.Diagnostics.PayloadByteLimit);
        RuntimeOptionsSelectedNodeTtlSecondsDraft =
            FormatInvariant(
                nodeOverride?.Diagnostics?.TtlSeconds
                    ?? draft.Workflow.Diagnostics.TtlSeconds);
        RuntimeOptionsSelectedNodeRedactColumnsDraft =
            FormatRuntimeOptionsRedactColumns(
                nodeOverride?.Diagnostics?.RedactColumns
                    ?? draft.Workflow.Diagnostics.RedactColumns);
        RuntimeOptionsSelectedNodeMaskPolicyDraft =
            nodeOverride?.Diagnostics?.MaskPolicy ?? draft.Workflow.Diagnostics.MaskPolicy;

        OnPropertyChanged(nameof(HasSelectedRuntimeOptionsNode));
        ResetRuntimeOptionsSelectedNodeOverrideCommand.NotifyCanExecuteChanged();
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    private bool TryBuildRuntimeOptionsDraftFromStructuredInputs(
        out RuntimeOptionsDraft draft,
        out string errorMessage)
    {
        var readResult = RuntimeOptionsDraftReader.Read(WorkflowDefinitionDraftJson);
        if (!readResult.Succeeded)
        {
            draft = new RuntimeOptionsDraft();
            errorMessage =
                LocalizeWorkflowDefinitionDraftWarning(readResult.Warning)
                ?? string.Empty;
            return false;
        }

        return TryBuildRuntimeOptionsDraftFromStructuredInputs(
            readResult.Draft,
            out draft,
            out errorMessage);
    }

    private bool TryBuildRuntimeOptionsDraftFromStructuredInputs(
        RuntimeOptionsDraft baseDraft,
        out RuntimeOptionsDraft draft,
        out string errorMessage)
    {
        draft = new RuntimeOptionsDraft();
        if (!TryBuildRuntimeOptionsWorkflowDraft(
            out var workflowDraft,
            out errorMessage))
        {
            return false;
        }

        var nodeOverrides =
            new Dictionary<string, RuntimeOptionsNodeOverrideDraft>(
                baseDraft.NodeOverrides);
        if (SelectedRuntimeOptionsNode is not null)
        {
            if (!TryBuildSelectedRuntimeOptionsNodeOverrideDraft(
                out var nodeOverride,
                out errorMessage))
            {
                return false;
            }

            nodeOverrides[SelectedRuntimeOptionsNode.NodeInstanceId] = nodeOverride;
        }

        draft = new RuntimeOptionsDraft
        {
            Version = RuntimeOptionsDefaults.Version,
            Workflow = workflowDraft,
            NodeOverrides = nodeOverrides,
        };
        return TryValidateRuntimeOptionsDraft(draft, out errorMessage);
    }

    private bool ApplyRuntimeOptionsDraftToWorkflow(RuntimeOptionsDraft draft)
    {
        var patchResult = WorkflowDefinitionDraftRuntimeOptionsPatcher.Apply(
            WorkflowDefinitionDraftJson,
            draft);
        if (!patchResult.Succeeded)
        {
            RuntimeOptionsEditorErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return false;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        RuntimeOptionsEditorErrorMessage = null;
        OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
        WorkflowDefinitionValidationMessage = T("definition.runtime_options_applied");
        WorkflowDefinitionValidationErrorMessage = null;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.runtime_options",
            UiNotificationKind.Success);
        if (IsRuntimeOptionsJsonEditorExpanded && !IsRuntimeOptionsJsonDraftDirty)
        {
            SetRuntimeOptionsJsonDraft(
                WorkflowDefinitionDraftRuntimeOptionsPatcher.FormatRuntimeOptions(draft),
                isDirty: false);
        }

        return true;
    }

    private void RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean()
    {
        if (!IsRuntimeOptionsJsonEditorExpanded || IsRuntimeOptionsJsonDraftDirty)
        {
            return;
        }

        if (!TryBuildRuntimeOptionsDraftFromStructuredInputs(
            out var draft,
            out _))
        {
            return;
        }

        SetRuntimeOptionsJsonDraft(
            WorkflowDefinitionDraftRuntimeOptionsPatcher.FormatRuntimeOptions(draft),
            isDirty: false);
    }

    private void SetRuntimeOptionsJsonDraft(string value, bool isDirty)
    {
        isSynchronizingRuntimeOptionsJsonDraft = true;
        RuntimeOptionsJsonDraft = value;
        isSynchronizingRuntimeOptionsJsonDraft = false;
        IsRuntimeOptionsJsonDraftDirty = isDirty;
    }

    private bool TryBuildRuntimeOptionsWorkflowDraft(
        out RuntimeOptionsWorkflowDraft draft,
        out string errorMessage)
    {
        draft = new RuntimeOptionsWorkflowDraft();
        errorMessage = string.Empty;
        if (!TryParseNonNegativeInt(
            RuntimeOptionsEventRateLimitPerSecondDraft,
            RuntimeOptionsEventRateLimitText,
            out var eventRateLimit,
            out errorMessage) ||
            !TryParseNonNegativeDouble(
                RuntimeOptionsProgressIntervalSecondsDraft,
                RuntimeOptionsProgressIntervalText,
                out var progressInterval,
                out errorMessage) ||
            !TryParseNonNegativeInt(
                RuntimeOptionsPayloadByteLimitDraft,
                RuntimeOptionsPayloadByteLimitText,
                out var payloadByteLimit,
                out errorMessage) ||
            !TryParseNonNegativeInt(
                RuntimeOptionsTtlSecondsDraft,
                RuntimeOptionsTtlSecondsText,
                out var ttlSeconds,
                out errorMessage))
        {
            return false;
        }

        draft = new RuntimeOptionsWorkflowDraft
        {
            Profile = RuntimeOptionsProfileDraft,
            StrictValidation = RuntimeOptionsStrictValidationDraft,
            Telemetry = new RuntimeOptionsTelemetryDraft
            {
                LogLevel = RuntimeOptionsLogLevelDraft,
                EventLevel = RuntimeOptionsEventLevelDraft,
                EventRateLimitPerSecond = eventRateLimit,
                ProgressEnabled = RuntimeOptionsProgressEnabledDraft,
                ProgressIntervalSeconds = progressInterval,
            },
            Diagnostics = new RuntimeOptionsDiagnosticsDraft
            {
                CaptureErrorContext = RuntimeOptionsCaptureErrorContextDraft,
                IncludeMetrics = RuntimeOptionsIncludeMetricsDraft,
                PayloadByteLimit = payloadByteLimit,
                TtlSeconds = ttlSeconds,
                RedactColumns = ParseRuntimeOptionsRedactColumns(
                    RuntimeOptionsRedactColumnsDraft),
                MaskPolicy = RuntimeOptionsMaskPolicyDraft,
            },
        };
        return true;
    }

    private bool TryBuildSelectedRuntimeOptionsNodeOverrideDraft(
        out RuntimeOptionsNodeOverrideDraft draft,
        out string errorMessage)
    {
        draft = new RuntimeOptionsNodeOverrideDraft();
        errorMessage = string.Empty;
        if (!TryParseNonNegativeInt(
            RuntimeOptionsSelectedNodeEventRateLimitPerSecondDraft,
            RuntimeOptionsEventRateLimitText,
            out var eventRateLimit,
            out errorMessage) ||
            !TryParseNonNegativeDouble(
                RuntimeOptionsSelectedNodeProgressIntervalSecondsDraft,
                RuntimeOptionsProgressIntervalText,
                out var progressInterval,
                out errorMessage) ||
            !TryParseNonNegativeInt(
                RuntimeOptionsSelectedNodePayloadByteLimitDraft,
                RuntimeOptionsPayloadByteLimitText,
                out var payloadByteLimit,
                out errorMessage) ||
            !TryParseNonNegativeInt(
                RuntimeOptionsSelectedNodeTtlSecondsDraft,
                RuntimeOptionsTtlSecondsText,
                out var ttlSeconds,
                out errorMessage))
        {
            return false;
        }

        draft = new RuntimeOptionsNodeOverrideDraft
        {
            Profile = RuntimeOptionsSelectedNodeProfileDraft,
            StrictValidation = RuntimeOptionsSelectedNodeStrictValidationDraft,
            Telemetry = new RuntimeOptionsTelemetryOverrideDraft
            {
                LogLevel = RuntimeOptionsSelectedNodeLogLevelDraft,
                EventLevel = RuntimeOptionsSelectedNodeEventLevelDraft,
                EventRateLimitPerSecond = eventRateLimit,
                ProgressEnabled = RuntimeOptionsSelectedNodeProgressEnabledDraft,
                ProgressIntervalSeconds = progressInterval,
            },
            Diagnostics = new RuntimeOptionsDiagnosticsOverrideDraft
            {
                CaptureErrorContext =
                    RuntimeOptionsSelectedNodeCaptureErrorContextDraft,
                IncludeMetrics = RuntimeOptionsSelectedNodeIncludeMetricsDraft,
                PayloadByteLimit = payloadByteLimit,
                TtlSeconds = ttlSeconds,
                RedactColumns = ParseRuntimeOptionsRedactColumns(
                    RuntimeOptionsSelectedNodeRedactColumnsDraft),
                MaskPolicy = RuntimeOptionsSelectedNodeMaskPolicyDraft,
            },
        };
        return true;
    }

    private bool TryValidateRuntimeOptionsDraft(
        RuntimeOptionsDraft draft,
        out string errorMessage)
    {
        if (!TryValidateRuntimeOptionsWorkflowDraft(draft.Workflow, out errorMessage))
        {
            return false;
        }

        foreach (var nodeOverride in draft.NodeOverrides.Values)
        {
            if (!TryValidateRuntimeOptionsNodeOverrideDraft(
                nodeOverride,
                out errorMessage))
            {
                return false;
            }
        }

        errorMessage = string.Empty;
        return true;
    }

    private bool TryValidateRuntimeOptionsWorkflowDraft(
        RuntimeOptionsWorkflowDraft draft,
        out string errorMessage)
    {
        if (!TryValidateRuntimeOptionsOption(
            RuntimeOptionsProfileValues,
            draft.Profile,
            RuntimeOptionsProfileText,
            out errorMessage) ||
            !TryValidateRuntimeOptionsTelemetryDraft(
                draft.Telemetry,
                out errorMessage) ||
            !TryValidateRuntimeOptionsDiagnosticsDraft(
                draft.Diagnostics,
                out errorMessage))
        {
            return false;
        }

        errorMessage = string.Empty;
        return true;
    }

    private bool TryValidateRuntimeOptionsTelemetryDraft(
        RuntimeOptionsTelemetryDraft draft,
        out string errorMessage)
    {
        if (!TryValidateRuntimeOptionsOption(
            RuntimeOptionsLogLevelValues,
            draft.LogLevel,
            RuntimeOptionsLogLevelText,
            out errorMessage) ||
            !TryValidateRuntimeOptionsOption(
                RuntimeOptionsEventLevelValues,
                draft.EventLevel,
                RuntimeOptionsEventLevelText,
                out errorMessage) ||
            !TryValidateRuntimeOptionsNonNegative(
                draft.EventRateLimitPerSecond,
                RuntimeOptionsEventRateLimitText,
                out errorMessage) ||
            !TryValidateRuntimeOptionsNonNegative(
                draft.ProgressIntervalSeconds,
                RuntimeOptionsProgressIntervalText,
                out errorMessage))
        {
            return false;
        }

        errorMessage = string.Empty;
        return true;
    }

    private bool TryValidateRuntimeOptionsDiagnosticsDraft(
        RuntimeOptionsDiagnosticsDraft draft,
        out string errorMessage)
    {
        if (!TryValidateRuntimeOptionsNonNegative(
            draft.PayloadByteLimit,
            RuntimeOptionsPayloadByteLimitText,
            out errorMessage) ||
            !TryValidateRuntimeOptionsNonNegative(
                draft.TtlSeconds,
                RuntimeOptionsTtlSecondsText,
                out errorMessage) ||
            !TryValidateRuntimeOptionsOption(
                RuntimeOptionsMaskPolicyValues,
                draft.MaskPolicy,
                RuntimeOptionsMaskPolicyText,
                out errorMessage))
        {
            return false;
        }

        errorMessage = string.Empty;
        return true;
    }

    private bool TryValidateRuntimeOptionsNodeOverrideDraft(
        RuntimeOptionsNodeOverrideDraft draft,
        out string errorMessage)
    {
        if (!TryValidateRuntimeOptionsOption(
            RuntimeOptionsProfileValues,
            draft.Profile,
            RuntimeOptionsProfileText,
            out errorMessage))
        {
            return false;
        }

        if (draft.Telemetry is not null &&
            !TryValidateRuntimeOptionsTelemetryOverrideDraft(
                draft.Telemetry,
                out errorMessage))
        {
            return false;
        }

        if (draft.Diagnostics is not null &&
            !TryValidateRuntimeOptionsDiagnosticsOverrideDraft(
                draft.Diagnostics,
                out errorMessage))
        {
            return false;
        }

        errorMessage = string.Empty;
        return true;
    }

    private bool TryValidateRuntimeOptionsTelemetryOverrideDraft(
        RuntimeOptionsTelemetryOverrideDraft draft,
        out string errorMessage)
    {
        if (!TryValidateRuntimeOptionsOption(
            RuntimeOptionsLogLevelValues,
            draft.LogLevel,
            RuntimeOptionsLogLevelText,
            out errorMessage) ||
            !TryValidateRuntimeOptionsOption(
                RuntimeOptionsEventLevelValues,
                draft.EventLevel,
                RuntimeOptionsEventLevelText,
                out errorMessage) ||
            !TryValidateRuntimeOptionsNonNegative(
                draft.EventRateLimitPerSecond,
                RuntimeOptionsEventRateLimitText,
                out errorMessage) ||
            !TryValidateRuntimeOptionsNonNegative(
                draft.ProgressIntervalSeconds,
                RuntimeOptionsProgressIntervalText,
                out errorMessage))
        {
            return false;
        }

        errorMessage = string.Empty;
        return true;
    }

    private bool TryValidateRuntimeOptionsDiagnosticsOverrideDraft(
        RuntimeOptionsDiagnosticsOverrideDraft draft,
        out string errorMessage)
    {
        if (!TryValidateRuntimeOptionsNonNegative(
            draft.PayloadByteLimit,
            RuntimeOptionsPayloadByteLimitText,
            out errorMessage) ||
            !TryValidateRuntimeOptionsNonNegative(
                draft.TtlSeconds,
                RuntimeOptionsTtlSecondsText,
                out errorMessage) ||
            !TryValidateRuntimeOptionsOption(
                RuntimeOptionsMaskPolicyValues,
                draft.MaskPolicy,
                RuntimeOptionsMaskPolicyText,
                out errorMessage))
        {
            return false;
        }

        errorMessage = string.Empty;
        return true;
    }

    private bool TryValidateRuntimeOptionsOption(
        IReadOnlyList<string> options,
        string? value,
        string label,
        out string errorMessage)
    {
        if (value is null || options.Contains(value, StringComparer.Ordinal))
        {
            errorMessage = string.Empty;
            return true;
        }

        errorMessage = F("definition.runtime_options_value_invalid", label);
        return false;
    }

    private bool TryValidateRuntimeOptionsNonNegative(
        int? value,
        string label,
        out string errorMessage)
    {
        if (!value.HasValue || value.Value >= 0)
        {
            errorMessage = string.Empty;
            return true;
        }

        errorMessage = F("definition.runtime_options_number_invalid", label);
        return false;
    }

    private bool TryValidateRuntimeOptionsNonNegative(
        double? value,
        string label,
        out string errorMessage)
    {
        if (!value.HasValue || value.Value >= 0)
        {
            errorMessage = string.Empty;
            return true;
        }

        errorMessage = F("definition.runtime_options_number_invalid", label);
        return false;
    }

    private bool TryParseNonNegativeInt(
        string input,
        string label,
        out int value,
        out string errorMessage)
    {
        if (int.TryParse(
            input,
            NumberStyles.Integer,
            CultureInfo.InvariantCulture,
            out value) &&
            value >= 0)
        {
            errorMessage = string.Empty;
            return true;
        }

        errorMessage = F("definition.runtime_options_number_invalid", label);
        return false;
    }

    private bool TryParseNonNegativeDouble(
        string input,
        string label,
        out double value,
        out string errorMessage)
    {
        if (double.TryParse(
            input,
            NumberStyles.Float,
            CultureInfo.InvariantCulture,
            out value) &&
            value >= 0)
        {
            errorMessage = string.Empty;
            return true;
        }

        errorMessage = F("definition.runtime_options_number_invalid", label);
        return false;
    }

    private static string FormatInvariant(int value)
    {
        return value.ToString(CultureInfo.InvariantCulture);
    }

    private static string FormatInvariant(double value)
    {
        return value.ToString(CultureInfo.InvariantCulture);
    }

    private static string FormatRuntimeOptionsRedactColumns(
        IReadOnlyList<string> redactColumns)
    {
        return string.Join(", ", redactColumns);
    }

    private static IReadOnlyList<string> ParseRuntimeOptionsRedactColumns(string input)
    {
        return input
            .Split([',', ';', '\r', '\n'], StringSplitOptions.TrimEntries)
            .Where(item => !string.IsNullOrWhiteSpace(item))
            .Distinct(StringComparer.Ordinal)
            .ToArray();
    }

    private void NotifyRuntimeOptionsSummaryChanged()
    {
        OnPropertyChanged(nameof(RuntimeOptionsSummaryText));
    }

    private IReadOnlyList<NodeConfigOptionItemViewModel> CreateRuntimeOptionsOptions(
        string group,
        IReadOnlyList<string> values)
    {
        return values
            .Select(value => new NodeConfigOptionItemViewModel(
                value,
                FormatRuntimeOptionsOptionValue(group, value)))
            .ToArray();
    }

    private string FormatRuntimeOptionsOptionValue(string group, string value)
    {
        return DisplayTextFormatter.FormatRuntimeOptionsOptionValue(group, value);
    }

    private string FormatSelectedRunRuntimeOptionsSummary()
    {
        if (SelectedRun is null)
        {
            return T("definition.runtime_options_run_summary_empty");
        }

        var definitionJson = FindSelectedRunDefinitionJson();
        if (definitionJson is null)
        {
            return T("definition.runtime_options_run_summary_unavailable");
        }

        var readResult = RuntimeOptionsDraftReader.Read(definitionJson);
        if (!readResult.Succeeded)
        {
            return LocalizeWorkflowDefinitionDraftWarning(readResult.Warning)
                ?? readResult.Warning
                ?? T("definition.runtime_options_run_summary_unavailable");
        }

        return F(
            "definition.runtime_options_run_summary",
            FormatRuntimeOptionsOptionValue("profile", readResult.Draft.Workflow.Profile),
            FormatRuntimeOptionsOptionValue(
                "event_level",
                readResult.Draft.Workflow.Telemetry.EventLevel),
            readResult.Draft.Workflow.Telemetry.ProgressEnabled
                ? T("common.on")
                : T("common.off"),
            readResult.Draft.NodeOverrides.Count);
    }

    private string? FindSelectedRunDefinitionJson()
    {
        if (SelectedRun is null ||
            WorkflowDefinitionDetail is null ||
            !string.Equals(
                SelectedRun.WorkflowId,
                WorkflowDefinitionDetail.WorkflowId,
                StringComparison.Ordinal))
        {
            return null;
        }

        if (string.Equals(
            SelectedRun.RevisionId,
            WorkflowDefinitionDetail.RevisionId,
            StringComparison.Ordinal) ||
            (string.IsNullOrWhiteSpace(SelectedRun.RevisionId) &&
                SelectedRun.WorkflowVersion == WorkflowDefinitionDetail.Version))
        {
            return WorkflowDefinitionDetail.RawDefinitionJson;
        }

        return WorkflowDefinitionDetail.Revisions.FirstOrDefault(revision =>
            string.Equals(
                revision.RevisionId,
                SelectedRun.RevisionId,
                StringComparison.Ordinal))?.RawDefinitionJson;
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

    private string? FormatDeletedRewiredConnectionsMessage(
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
            "definition.node_delete_rewired_connections",
            removedText,
            addedText);
    }

    private string? FormatMovedRewiredConnectionsMessage(
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
            "definition.node_move_rewired_connections",
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

    private (string? InputPort, string? OutputPort, string? SourceOutputPort) TryGetAutoWirePorts()
    {
        var definition = SelectedNewDraftNodeDefinition;
        if (definition is null)
        {
            return (null, null, null);
        }

        var inputPort = TryGetSingleInputPort(definition.InputPorts);
        if (inputPort is null)
        {
            return (null, null, null);
        }

        return (
            inputPort,
            TryGetPreferredOutputPort(definition.OutputPorts),
            TryGetSourceAutoWireOutputPort());
    }

    private string? TryGetSourceAutoWireOutputPort()
    {
        if (SelectedWorkflowDefinitionNode is null)
        {
            return null;
        }

        var sourceDefinition = FindNodeDefinition(SelectedWorkflowDefinitionNode);
        return sourceDefinition is null
            ? null
            : TryGetPreferredOutputPort(sourceDefinition.OutputPorts);
    }

    private static string? TryGetSingleInputPort(
        IReadOnlyList<NodePortDefinitionDto> inputPorts)
    {
        return inputPorts.Count == 1 ? inputPorts[0].Name : null;
    }

    private static string? TryGetPreferredOutputPort(
        IReadOnlyList<NodePortDefinitionDto> outputPorts)
    {
        if (outputPorts.Count == 0)
        {
            return null;
        }

        var outPort = outputPorts.FirstOrDefault(port =>
            string.Equals(port.Name, "out", StringComparison.Ordinal));
        if (outPort is not null)
        {
            return outPort.Name;
        }

        return outputPorts.Count == 1 ? outputPorts[0].Name : null;
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

    partial void OnIsLoadingWorkflowDefinitionChanged(bool value)
    {
        LoadSelectedWorkflowDefinitionCommand.NotifyCanExecuteChanged();
    }

    partial void OnWorkflowDefinitionDetailChanged(WorkflowDefinitionDetailViewModel? value)
    {
        ClearWorkflowDefinitionDraftBatchSelection();
        ResetWorkflowDefinitionStructuredEditInput();
        OnPropertyChanged(nameof(HasWorkflowDefinition));
        OnPropertyChanged(nameof(SelectedRunRuntimeOptionsSummaryText));
        RefreshSelectedNodeDisplayNameDraftState();
        RefreshSelectedNodeConfigDraftState();
        RefreshRuntimeOptionsDraftState();
        ApplySelectedNodeDisplayNameDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
        ApplyRuntimeOptionsDraftCommand.NotifyCanExecuteChanged();
        RegenerateRuntimeOptionsJsonDraftCommand.NotifyCanExecuteChanged();
        ResetRuntimeOptionsSelectedNodeOverrideCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeDisplayNameDraftCommand.NotifyCanExecuteChanged();
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
        SelectedRuntimeOptionsNode = value;
        ApplySelectedNodeDisplayNameDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
        NotifyWorkflowDefinitionNodeActionCommandsChanged();
        RefreshSelectedWorkflowNodeDataPreviewCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
    }

    partial void OnSelectedRuntimeOptionsNodeChanged(
        WorkflowDefinitionNodeListItemViewModel? value)
    {
        OnPropertyChanged(nameof(HasSelectedRuntimeOptionsNode));
        RefreshSelectedRuntimeOptionsNodeDraftState();
        ResetRuntimeOptionsSelectedNodeOverrideCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsRuntimeOptionsJsonEditorExpandedChanged(bool value)
    {
        if (value && !IsRuntimeOptionsJsonDraftDirty)
        {
            RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
        }
    }

    partial void OnRuntimeOptionsJsonDraftChanged(string value)
    {
        if (!isSynchronizingRuntimeOptionsJsonDraft)
        {
            IsRuntimeOptionsJsonDraftDirty = true;
        }
    }

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

    partial void OnRuntimeOptionsSelectedNodeProfileDraftChanged(string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeStrictValidationDraftChanged(bool value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeLogLevelDraftChanged(string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeEventLevelDraftChanged(string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeEventRateLimitPerSecondDraftChanged(
        string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeProgressEnabledDraftChanged(bool value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeProgressIntervalSecondsDraftChanged(
        string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeCaptureErrorContextDraftChanged(bool value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeIncludeMetricsDraftChanged(bool value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodePayloadByteLimitDraftChanged(string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeTtlSecondsDraftChanged(string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeRedactColumnsDraftChanged(string value)
    {
        RefreshRuntimeOptionsJsonDraftFromStructuredInputsIfClean();
    }

    partial void OnRuntimeOptionsSelectedNodeMaskPolicyDraftChanged(string value)
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
        RefreshRuntimeOptionsDraftState();

        IsWorkflowDefinitionDraftDirty = value != originalWorkflowDefinitionJson;

        if (WorkflowDefinitionValidationMessage == T("definition.draft_valid") ||
            WorkflowDefinitionValidationMessage == T("definition.draft_has_issues") ||
            WorkflowDefinitionValidationMessage == T("definition.validation_failed"))
        {
            WorkflowDefinitionValidationMessage = T("definition.validation_invalidated");
            WorkflowDefinitionValidationErrorMessage = null;
        }

        ValidateWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        RestoreWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeDisplayNameDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
        ApplyRuntimeOptionsDraftCommand.NotifyCanExecuteChanged();
        RegenerateRuntimeOptionsJsonDraftCommand.NotifyCanExecuteChanged();
        ResetRuntimeOptionsSelectedNodeOverrideCommand.NotifyCanExecuteChanged();
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
        if (SelectedRuntimeOptionsNode is not null &&
            !WorkflowDefinitionDraftNodes.Contains(SelectedRuntimeOptionsNode))
        {
            SelectedRuntimeOptionsNode = null;
        }

        NotifyWorkflowDefinitionNodeActionCommandsChanged();
    }

    partial void OnIsWorkflowDefinitionDraftDirtyChanged(bool value)
    {
        RestoreWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        SaveWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        StartSelectedWorkflowCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
        OnPropertyChanged(nameof(WorkflowRunGuardText));
    }

    partial void OnHasWorkflowDefinitionRevisionConflictChanged(bool value)
    {
        ApplySelectedNodeDisplayNameDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
        ApplyRuntimeOptionsDraftCommand.NotifyCanExecuteChanged();
        RegenerateRuntimeOptionsJsonDraftCommand.NotifyCanExecuteChanged();
        ResetRuntimeOptionsSelectedNodeOverrideCommand.NotifyCanExecuteChanged();
        AddWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
        NotifyWorkflowDefinitionNodeActionCommandsChanged();
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        DeleteWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        SaveWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        StartSelectedWorkflowCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
        OnPropertyChanged(nameof(WorkflowRunGuardText));
    }

    partial void OnIsValidatingWorkflowDefinitionDraftChanged(bool value)
    {
        OnPropertyChanged(nameof(IsWorkflowDefinitionDraftBusy));
        ValidateWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        RestoreWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeDisplayNameDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
        ApplyRuntimeOptionsDraftCommand.NotifyCanExecuteChanged();
        RegenerateRuntimeOptionsJsonDraftCommand.NotifyCanExecuteChanged();
        ResetRuntimeOptionsSelectedNodeOverrideCommand.NotifyCanExecuteChanged();
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
        RestoreWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeDisplayNameDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
        ApplyRuntimeOptionsDraftCommand.NotifyCanExecuteChanged();
        RegenerateRuntimeOptionsJsonDraftCommand.NotifyCanExecuteChanged();
        ResetRuntimeOptionsSelectedNodeOverrideCommand.NotifyCanExecuteChanged();
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
        NotifyWorkflowDefinitionNodeActionDisabledReasonsChanged();
    }

    private void NotifyWorkflowDefinitionNodeActionDisabledReasonsChanged()
    {
        OnPropertyChanged(nameof(CopyWorkflowDefinitionDraftNodeDisabledReasonText));
        OnPropertyChanged(nameof(DeleteWorkflowDefinitionDraftNodeDisabledReasonText));
        OnPropertyChanged(nameof(DeleteSelectedWorkflowDefinitionDraftNodesDisabledReasonText));
        OnPropertyChanged(nameof(MoveSelectedWorkflowDefinitionDraftNodeUpDisabledReasonText));
        OnPropertyChanged(nameof(MoveSelectedWorkflowDefinitionDraftNodeDownDisabledReasonText));
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

    partial void OnIsLoadingRuntimeEventLogChanged(bool value)
    {
        OnPropertyChanged(nameof(IsLogBusy));
        RefreshRuntimeEventLogCommand.NotifyCanExecuteChanged();
    }

    partial void OnRuntimeEventLogErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasRuntimeEventLogError));
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

    partial void OnIsLoadingDataPreviewWorkbenchChanged(bool value)
    {
        OnPropertyChanged(nameof(IsDataPreviewWorkbenchBusy));
        LoadSelectedDataPreviewTableCommand.NotifyCanExecuteChanged();
        LoadPreviousDataPreviewWorkbenchPageCommand.NotifyCanExecuteChanged();
        LoadNextDataPreviewWorkbenchPageCommand.NotifyCanExecuteChanged();
        ParseDataPreviewWorkbenchPasteCommand.NotifyCanExecuteChanged();
        RestoreDataPreviewWorkbenchDraftCommand.NotifyCanExecuteChanged();
        SaveDataPreviewWorkbenchAsCommand.NotifyCanExecuteChanged();
        ShowDataPreviewDetailsCommand.NotifyCanExecuteChanged();
    }

    partial void OnTableRefErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasTableRefError));
    }

    partial void OnDataPreviewErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasDataPreviewError));
    }

    partial void OnDataPreviewWorkbenchErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasDataPreviewWorkbenchError));
    }

    partial void OnDataPreviewWorkbenchSearchTextChanged(string value)
    {
        DataPreviewWorkbenchClipboardText = string.Empty;
        ApplyDataPreviewWorkbenchSearch();
        UpdateDataPreviewWorkbenchLoadedMessage();
    }

    partial void OnDataPreviewWorkbenchClipboardTextChanged(string value)
    {
        OnPropertyChanged(nameof(HasDataPreviewWorkbenchClipboardText));
    }

    partial void OnDataPreviewWorkbenchPasteTextChanged(string value)
    {
        OnPropertyChanged(nameof(HasDataPreviewWorkbenchPasteText));
        ParseDataPreviewWorkbenchPasteCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsDataPreviewWorkbenchDraftChanged(bool value)
    {
        OnPropertyChanged(nameof(DataPreviewWorkbenchSourceText));
    }

    partial void OnSelectedDataPreviewStateChanged(DataPreviewStateListItemViewModel? value)
    {
        var previousTableRefId = SelectedDataPreviewTableOption?.TableRefId;
        DataPreviewTableOptions.Clear();
        if (value is not null)
        {
            foreach (var tableRef in value.TableRefs)
            {
                DataPreviewTableOptions.Add(tableRef);
            }
        }

        SelectedDataPreviewTableOption =
            DataPreviewTableOptions.FirstOrDefault(tableRef =>
                string.Equals(tableRef.TableRefId, previousTableRefId, StringComparison.Ordinal))
            ?? DataPreviewTableOptions.FirstOrDefault();
    }

    partial void OnSelectedDataPreviewTableOptionChanged(TableRefListItemViewModel? value)
    {
        LoadSelectedDataPreviewTableCommand.NotifyCanExecuteChanged();
    }

    partial void OnLoadedDataPreviewTableRefChanged(TableRefListItemViewModel? value)
    {
        OnPropertyChanged(nameof(DataPreviewWorkbenchSourceText));
        OnPropertyChanged(nameof(CanSaveDataPreviewWorkbenchAsDraft));
        OnPropertyChanged(nameof(DataPreviewWorkbenchSavePolicyText));
        LoadPreviousDataPreviewWorkbenchPageCommand.NotifyCanExecuteChanged();
        LoadNextDataPreviewWorkbenchPageCommand.NotifyCanExecuteChanged();
        SaveDataPreviewWorkbenchAsCommand.NotifyCanExecuteChanged();
    }

    partial void OnSelectedDataPreviewTableRefChanged(TableRefListItemViewModel? value)
    {
        DataPreviewWorkbenchErrorMessage = null;
        if (value is not null)
        {
            SelectDataPreviewTableOptionByTableRefId(value.TableRefId);
        }

        LoadSelectedDataPreviewTableCommand.NotifyCanExecuteChanged();
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
        IsLoadingRuntimeEventLog = false;
        RefreshRuntimeEventLogCommand.NotifyCanExecuteChanged();
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
