using System.Collections.ObjectModel;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public ObservableCollection<TableDataPreviewColumnViewModel> DataPreviewColumns { get; } = new();

    public ObservableCollection<TableDataPreviewRowViewModel> DataPreviewRows { get; } =
        new();
}
