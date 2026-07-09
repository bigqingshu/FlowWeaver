using System.Text.Json;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private static TableDataRowsDto CreateDataPreviewWorkbenchDraftRows(
        string[] columns,
        JsonElement[] rows)
    {
        return new TableDataRowsDto
        {
            TableRefId = "local-draft",
            Offset = 0,
            Limit = rows.Length,
            RowCount = rows.Length,
            Columns = columns,
            Rows = rows,
            HasMore = false,
        };
    }
}
