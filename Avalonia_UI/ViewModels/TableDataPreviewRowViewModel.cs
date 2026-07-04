using System.Collections.Generic;

namespace Avalonia_UI.ViewModels;

public sealed class TableDataPreviewRowViewModel
{
    public TableDataPreviewRowViewModel(IReadOnlyList<string> cells)
    {
        Cells = cells;
    }

    public IReadOnlyList<string> Cells { get; }
}
