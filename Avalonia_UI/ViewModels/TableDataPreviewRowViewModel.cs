using System.Collections.Generic;
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

    [ObservableProperty]
    private string text;

    public TableDataPreviewCellViewModel(
        string text,
        System.Action<string>? textChanged = null)
    {
        this.text = text;
        this.textChanged = textChanged;
    }

    partial void OnTextChanged(string value)
    {
        textChanged?.Invoke(value);
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
