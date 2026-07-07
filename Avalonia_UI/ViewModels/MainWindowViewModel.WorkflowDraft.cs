using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private int nodeDefinitionsLoadVersion;
    private bool hasLoadedNodeDefinitionCatalog;
    private string? loadedNodeDefinitionCatalogConnectionKey;
    private string? loadedNodeDefinitionCatalogHash;
    private string? loadedNodeDefinitionCatalogProgramHash;
    private readonly Dictionary<(string NodeType, string NodeVersion), NodeDefinitionListItemViewModel>
        nodeDefinitionByKey = new();
    private readonly Dictionary<string, NodeConfigSchemaParseResult> nodeConfigSchemaByKey =
        new(StringComparer.Ordinal);
    private readonly WorkflowDefinitionDraftParseCache workflowDefinitionDraftParseCache = new();
    private string? nodeConfigSchemaCacheCatalogKey;

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

    public ObservableCollection<NodeDefinitionListItemViewModel> NodeDefinitions { get; } =
        new();

    public ObservableCollection<WorkflowDefinitionNodeListItemViewModel>
        WorkflowDefinitionDraftNodes { get; } = new();

    public ObservableCollection<NodeConfigEditableFieldInputViewModel>
        SelectedNodeConfigEditableInputFields { get; } = new();

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

    public string NodeMoveSemanticsText => T("definition.node_move_semantics");

    public string WorkflowLinearChainStatusText
    {
        get
        {
            if (string.IsNullOrWhiteSpace(WorkflowDefinitionDraftJson))
            {
                return T("definition.linear_chain_status_not_loaded");
            }

            var analysis = ReadWorkflowDefinitionLinearChainAnalysisFromCache();
            if (analysis is null)
            {
                return T("definition.linear_chain_status_not_loaded");
            }

            return analysis.IsLinear
                ? F(
                    "definition.linear_chain_status_linear",
                    analysis.NodeInstanceIds.Count)
                : F(
                    "definition.linear_chain_status_not_linear",
                    LocalizeWorkflowDefinitionDraftWarning(analysis.Warning));
        }
    }

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
        await RefreshNodeDefinitionsCoreAsync(allowStateCacheHit: false);
    }

    private async Task RefreshNodeDefinitionsCoreAsync(bool allowStateCacheHit)
    {
        var requestVersion = ++nodeDefinitionsLoadVersion;
        IsLoadingNodeDefinitions = true;
        NodeDefinitionCatalogMessage = T("node_catalog.loading");
        NodeDefinitionCatalogErrorMessage = null;
        var settings = BuildSettings();
        var connectionKey = BuildNodeDefinitionConnectionKey(settings);

        try
        {
            var catalogState = await TryGetNodeDefinitionCatalogStateAsync(settings);
            if (requestVersion != nodeDefinitionsLoadVersion)
            {
                return;
            }

            if (allowStateCacheHit
                && IsNodeDefinitionCatalogCacheHit(connectionKey, catalogState))
            {
                NodeDefinitionCatalogMessage =
                    F("format.loaded_node_definitions", NodeDefinitions.Count);
                OnPropertyChanged(nameof(HasNodeDefinitions));
                OnPropertyChanged(nameof(HasNodeDefinitionCatalogEmptyState));
                return;
            }

            var response = await _apiClient.ListNodeDefinitionsAsync(
                settings,
                _shutdown.Token);

            if (requestVersion != nodeDefinitionsLoadVersion)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                SelectedNewDraftNodeDefinition = null;
                NodeDefinitions.Clear();
                nodeDefinitionByKey.Clear();
                var schemaCatalogKey = PrepareNodeConfigSchemaCache(
                    connectionKey,
                    catalogState);
                foreach (var definition in response.Data
                    .OrderBy(definition => definition.DisplayName)
                    .ThenBy(definition => definition.NodeType)
                    .ThenBy(definition => definition.NodeVersion))
                {
                    var item = new NodeDefinitionListItemViewModel(
                        definition,
                        DisplayTextFormatter,
                        GetOrParseNodeConfigSchema(definition, schemaCatalogKey));
                    NodeDefinitions.Add(item);
                    nodeDefinitionByKey[BuildNodeDefinitionLookupKey(item.NodeType, item.NodeVersion)] =
                        item;
                }

                RecordNodeDefinitionCatalogCacheState(connectionKey, catalogState);
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
        if (!CanRefreshNodeDefinitions())
        {
            return;
        }

        await RefreshNodeDefinitionsCoreAsync(allowStateCacheHit: true);
    }

    private async Task<NodeDefinitionCatalogStateDto?> TryGetNodeDefinitionCatalogStateAsync(
        EngineHostConnectionSettings settings)
    {
        try
        {
            var response = await _apiClient.GetNodeDefinitionCatalogStateAsync(
                settings,
                _shutdown.Token);
            if (response.Ok
                && response.Data is { } state
                && !string.IsNullOrWhiteSpace(state.CatalogHash))
            {
                return state;
            }
        }
        catch (NotSupportedException)
        {
        }

        return null;
    }

    private bool IsNodeDefinitionCatalogCacheHit(
        string connectionKey,
        NodeDefinitionCatalogStateDto? catalogState)
    {
        var catalogHash = NormalizeNodeDefinitionCatalogToken(catalogState?.CatalogHash);
        if (!hasLoadedNodeDefinitionCatalog || catalogHash is null)
        {
            return false;
        }

        return string.Equals(
                loadedNodeDefinitionCatalogConnectionKey,
                connectionKey,
                StringComparison.Ordinal)
            && string.Equals(
                loadedNodeDefinitionCatalogHash,
                catalogHash,
                StringComparison.Ordinal)
            && string.Equals(
                loadedNodeDefinitionCatalogProgramHash,
                NormalizeNodeDefinitionCatalogToken(catalogState?.ProgramHash),
                StringComparison.Ordinal);
    }

    private void RecordNodeDefinitionCatalogCacheState(
        string connectionKey,
        NodeDefinitionCatalogStateDto? catalogState)
    {
        hasLoadedNodeDefinitionCatalog = true;
        loadedNodeDefinitionCatalogConnectionKey = connectionKey;
        loadedNodeDefinitionCatalogHash =
            NormalizeNodeDefinitionCatalogToken(catalogState?.CatalogHash);
        loadedNodeDefinitionCatalogProgramHash =
            NormalizeNodeDefinitionCatalogToken(catalogState?.ProgramHash);
    }

    private void InvalidateNodeDefinitionCatalogCacheState()
    {
        hasLoadedNodeDefinitionCatalog = false;
        loadedNodeDefinitionCatalogConnectionKey = null;
        loadedNodeDefinitionCatalogHash = null;
        loadedNodeDefinitionCatalogProgramHash = null;
    }

    private string? PrepareNodeConfigSchemaCache(
        string connectionKey,
        NodeDefinitionCatalogStateDto? catalogState)
    {
        var catalogKey = BuildNodeConfigSchemaCatalogKey(connectionKey, catalogState);
        if (!string.Equals(
            nodeConfigSchemaCacheCatalogKey,
            catalogKey,
            StringComparison.Ordinal))
        {
            nodeConfigSchemaByKey.Clear();
            nodeConfigSchemaCacheCatalogKey = catalogKey;
        }

        return catalogKey;
    }

    private NodeConfigSchemaParseResult GetOrParseNodeConfigSchema(
        NodeDefinitionDto definition,
        string? schemaCatalogKey)
    {
        if (schemaCatalogKey is null)
        {
            return NodeConfigSchemaParser.Parse(
                definition.ConfigSchemaVersion,
                definition.ConfigSchema);
        }

        var schemaCacheKey = BuildNodeConfigSchemaCacheKey(definition);
        if (nodeConfigSchemaByKey.TryGetValue(schemaCacheKey, out var cached))
        {
            return cached;
        }

        var parsed = NodeConfigSchemaParser.Parse(
            definition.ConfigSchemaVersion,
            definition.ConfigSchema);
        nodeConfigSchemaByKey[schemaCacheKey] = parsed;
        return parsed;
    }

    private static string? BuildNodeConfigSchemaCatalogKey(
        string connectionKey,
        NodeDefinitionCatalogStateDto? catalogState)
    {
        var catalogHash = NormalizeNodeDefinitionCatalogToken(catalogState?.CatalogHash);
        if (catalogHash is null)
        {
            return null;
        }

        return string.Concat(
            connectionKey,
            "|program:",
            NormalizeNodeDefinitionCatalogToken(catalogState?.ProgramHash) ?? string.Empty,
            "|catalog:",
            catalogHash);
    }

    private static string BuildNodeConfigSchemaCacheKey(NodeDefinitionDto definition)
    {
        return string.Concat(
            definition.NodeType,
            "@",
            definition.NodeVersion,
            "|schema:",
            definition.ConfigSchemaVersion);
    }

    private static (string NodeType, string NodeVersion) BuildNodeDefinitionLookupKey(
        string nodeType,
        string nodeVersion)
    {
        return (nodeType, nodeVersion);
    }

    private static string BuildNodeDefinitionConnectionKey(
        EngineHostConnectionSettings settings)
    {
        return string.Concat(
            NormalizeNodeDefinitionBaseUrl(settings.BaseUrl),
            "|token:",
            ComputeNodeDefinitionTokenFingerprint(settings.Token));
    }

    private static string NormalizeNodeDefinitionBaseUrl(string baseUrl)
    {
        var trimmed = baseUrl.Trim();
        if (Uri.TryCreate(trimmed, UriKind.Absolute, out var uri))
        {
            return uri.GetLeftPart(UriPartial.Authority)
                .TrimEnd('/')
                .ToLowerInvariant();
        }

        return trimmed.ToLowerInvariant();
    }

    private static string ComputeNodeDefinitionTokenFingerprint(string token)
    {
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(token));
        return Convert.ToHexString(hash.AsSpan(0, 8)).ToLowerInvariant();
    }

    private static string? NormalizeNodeDefinitionCatalogToken(string? value)
    {
        var trimmed = value?.Trim();
        return string.IsNullOrEmpty(trimmed) ? null : trimmed;
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
        return nodeDefinitionByKey.TryGetValue(
            BuildNodeDefinitionLookupKey(node.NodeType, node.NodeVersion),
            out var definition)
                ? definition
                : null;
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
        WorkflowDefinitionDraftStructure =
            ReadWorkflowDefinitionDraftStructureFromCache();
        RefreshWorkflowDefinitionDraftNodes();
        ClearSelectedWorkflowDefinitionDraftNodeIfMissing();
        ClearSelectedWorkflowDefinitionDraftConnectionIfMissing();
        ClearSelectedNewDraftConnectionNodesIfMissing();
    }

    private WorkflowDefinitionDraftStructure? ReadWorkflowDefinitionDraftStructureFromCache()
    {
        return workflowDefinitionDraftParseCache.GetStructure(
            WorkflowDefinitionDraftJson,
            DisplayTextFormatter);
    }

    private WorkflowDefinitionLinearChainAnalysis?
        ReadWorkflowDefinitionLinearChainAnalysisFromCache()
    {
        return workflowDefinitionDraftParseCache.GetLinearChainAnalysis(
            WorkflowDefinitionDraftJson);
    }

    private RuntimeOptionsDraftReadResult
        ReadWorkflowDefinitionDraftRuntimeOptionsFromCache()
    {
        return workflowDefinitionDraftParseCache.GetRuntimeOptions(
            WorkflowDefinitionDraftJson);
    }

    private void InvalidateWorkflowDefinitionDraftParseCache()
    {
        workflowDefinitionDraftParseCache.Invalidate();
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

}
