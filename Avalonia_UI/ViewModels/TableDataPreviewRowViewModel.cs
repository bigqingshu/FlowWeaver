using System.Collections.Generic;
using System.Diagnostics.CodeAnalysis;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public sealed class TableDataPreviewColumnViewModel
{
    public TableDataPreviewColumnViewModel(string name)
    {
        Name = name;
    }

    public string Name { get; }
}

public sealed partial class TableDataPreviewCellViewModel : ObservableObject
{
    private readonly System.Action<string>? textChanged;

    private string text;

    [AllowNull]
    public string Text
    {
        get => text;
        set
        {
            var normalized = value ?? string.Empty;
            if (SetProperty(ref text, normalized))
            {
                textChanged?.Invoke(normalized);
            }
        }
    }

    public TableDataPreviewCellViewModel(
        string text,
        System.Action<string>? textChanged = null)
    {
        this.text = text ?? string.Empty;
        this.textChanged = textChanged;
    }

}

public sealed class TableDataPreviewRowViewModel
{
    public TableDataPreviewRowViewModel(IReadOnlyList<TableDataPreviewCellViewModel> cells)
    {
        Cells = cells;
    }

    public IReadOnlyList<TableDataPreviewCellViewModel> Cells { get; }
}
