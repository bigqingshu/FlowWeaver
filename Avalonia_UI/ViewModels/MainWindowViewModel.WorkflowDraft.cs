using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
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
    private string lastSuggestedNewDraftConnectionId = string.Empty;
    private int workflowDefinitionLoadVersion = 0;

    public ObservableCollection<WorkflowDefinitionNodeListItemViewModel>
        WorkflowDefinitionDraftNodes { get; } = new();

    public bool HasSelectedWorkflowDefinitionNode => SelectedWorkflowDefinitionNode is not null;

    public bool HasNoSelectedWorkflowDefinitionNode => SelectedWorkflowDefinitionNode is null;

}
