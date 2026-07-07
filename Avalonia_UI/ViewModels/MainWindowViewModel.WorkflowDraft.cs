using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
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
    [ObservableProperty]
    private bool isLoadingWorkflowDefinition;

    [ObservableProperty]
    private WorkflowDefinitionDetailViewModel? workflowDefinitionDetail;

    [ObservableProperty]
    private WorkflowDefinitionNodeListItemViewModel? selectedWorkflowDefinitionNode;

    [ObservableProperty]
    private string workflowDefinitionMessage = "Select a workflow to load definition.";

    [ObservableProperty]
    private string? workflowDefinitionErrorMessage;

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

    public ObservableCollection<WorkflowDefinitionNodeListItemViewModel>
        WorkflowDefinitionDraftNodes { get; } = new();

    public bool HasSelectedWorkflowDefinitionNode => SelectedWorkflowDefinitionNode is not null;

    public bool HasNoSelectedWorkflowDefinitionNode => SelectedWorkflowDefinitionNode is null;

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

    public string NodesSectionText => T("definition.nodes");

    public string WorkflowNodesSectionText => T("definition.workflow_nodes");

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

    private void RefreshWorkflowDefinitionDraftStructureState()
    {
        WorkflowDefinitionDraftStructure =
            ReadWorkflowDefinitionDraftStructureFromCache();
        RefreshWorkflowDefinitionDraftNodes();
        ClearSelectedWorkflowDefinitionDraftNodeIfMissing();
        ClearSelectedWorkflowDefinitionDraftConnectionIfMissing();
        ClearSelectedNewDraftConnectionNodesIfMissing();
    }

    private void ResetWorkflowDefinitionDraftSelectionInput()
    {
        SelectedWorkflowDefinitionDraftNodeInstanceId = string.Empty;
        SelectedWorkflowDefinitionDraftConnectionId = string.Empty;
    }

    private void ResetWorkflowDefinitionStructuredEditInput()
    {
        lastSuggestedNewDraftNodeInstanceId = string.Empty;
        lastSuggestedNewDraftConnectionId = string.Empty;
        ResetNewDraftNodeInput();
        ResetNewDraftConnectionInput();
        ResetWorkflowDefinitionDraftSelectionInput();
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

}
