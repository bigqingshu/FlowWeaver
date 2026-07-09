using System.Linq;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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
}
