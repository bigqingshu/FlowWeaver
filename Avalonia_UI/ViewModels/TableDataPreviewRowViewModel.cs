using System.Collections.Generic;

namespace Avalonia_UI.ViewModels;

public sealed class TableDataPreviewColumnViewModel
{
    public TableDataPreviewColumnViewModel(string name)
    {
        Name = name;
    }

    public string Name { get; }
}

public sealed class TableDataPreviewCellViewModel
{
    public TableDataPreviewCellViewModel(string text)
    {
        Text = text;
    }

    public string Text { get; }
}

public sealed class TableDataPreviewRowViewModel
{
    public TableDataPreviewRowViewModel(IReadOnlyList<TableDataPreviewCellViewModel> cells)
    {
        Cells = cells;
    }

    public IReadOnlyList<TableDataPreviewCellViewModel> Cells { get; }
}
