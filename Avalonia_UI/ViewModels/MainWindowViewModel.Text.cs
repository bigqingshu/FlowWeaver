namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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
}
