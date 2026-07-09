using System.Collections.ObjectModel;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public ObservableCollection<SharedPublicationListItemViewModel> SharedPublications { get; } =
        new();
}
