using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private bool isRuntimeEventStreamRunning;

    [ObservableProperty]
    private bool isRuntimeEventStreamConnected;

    [ObservableProperty]
    private string runtimeEventStreamMessage = "Event stream disconnected.";

    [ObservableProperty]
    private string? runtimeEventStreamErrorMessage;

    [ObservableProperty]
    private long? lastRuntimeEventSequenceNumber;

    public ObservableCollection<RuntimeEventListItemViewModel> RuntimeEvents { get; } = new();

    public bool HasRuntimeEventStreamError =>
        !string.IsNullOrWhiteSpace(RuntimeEventStreamErrorMessage);

    public bool HasRuntimeEvents => RuntimeEvents.Count > 0;

    partial void OnIsRuntimeEventStreamRunningChanged(bool value)
    {
        StartRuntimeEventStreamCommand.NotifyCanExecuteChanged();
        StopRuntimeEventStreamCommand.NotifyCanExecuteChanged();
    }

    partial void OnRuntimeEventStreamErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasRuntimeEventStreamError));
    }
}
