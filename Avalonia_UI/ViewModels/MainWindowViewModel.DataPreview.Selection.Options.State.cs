using System.Collections.ObjectModel;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public ObservableCollection<DataPreviewStateListItemViewModel> DataPreviewStates { get; } = new();

    public ObservableCollection<TableRefListItemViewModel> DataPreviewTableOptions { get; } = new();
}
