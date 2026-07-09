namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public string DataPreviewSourceText =>
        !string.IsNullOrWhiteSpace(dataPreviewSourceWorkflowRunId)
        && !string.IsNullOrWhiteSpace(dataPreviewSourceNodeInstanceId)
        && !string.IsNullOrWhiteSpace(dataPreviewSourceLogicalTableId)
            ? FormatDataPreviewSourceText()
            : T("data_preview.source_not_loaded");

    public string DataPreviewSectionText => T("definition.data_preview");

    public string DataPreviewEmptyText => T("definition.data_preview_empty");

    public string DataPreviewPendingText => T("definition.data_preview_pending");

    public string DataPreviewRefreshText => T("definition.data_preview_refresh");

    public string PreviewSelectedNodeText => T("definition.preview_selected_node");

    public string TableRefsSectionText => T("data.table_refs");

    private string FormatDataPreviewSourceText()
    {
        if (string.Equals(
                dataPreviewSourceRunMode,
                "preview_to_node",
                System.StringComparison.OrdinalIgnoreCase))
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
}
