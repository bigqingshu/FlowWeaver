using System.Collections.ObjectModel;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public ObservableCollection<TableDataPreviewColumnViewModel> DataPreviewWorkbenchColumns { get; } = new();

    public ObservableCollection<TableDataPreviewRowViewModel> DataPreviewWorkbenchRows { get; } =
        new();
}
