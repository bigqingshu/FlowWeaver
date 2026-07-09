using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private string sharedPublicationMessage = "No shared publications loaded.";

    [ObservableProperty]
    private string? sharedPublicationErrorMessage;

    public bool HasSharedPublicationError =>
        !string.IsNullOrWhiteSpace(SharedPublicationErrorMessage);

    partial void OnSharedPublicationErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasSharedPublicationError));
    }
}
