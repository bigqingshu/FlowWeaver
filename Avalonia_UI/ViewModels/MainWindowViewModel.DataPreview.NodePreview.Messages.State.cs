using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private string dataPreviewMessage =
        "Select a run and workflow node to load data preview.";

    [ObservableProperty]
    private string? dataPreviewErrorMessage;
}
