using System.Collections.ObjectModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public ObservableCollection<RuntimeEventListItemViewModel> RuntimeEvents { get; } = new();

    public bool HasRuntimeEvents => RuntimeEvents.Count > 0;
}
