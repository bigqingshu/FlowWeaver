using Avalonia_UI.Api;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private string baseUrl = EngineHostConnectionSettings.DefaultBaseUrl;

    [ObservableProperty]
    private string token = string.Empty;

    [ObservableProperty]
    private ConnectionStatus connectionStatus = ConnectionStatus.Disconnected;

    [ObservableProperty]
    private bool isAuthenticationFailed;

    [ObservableProperty]
    private string statusMessage = "Disconnected.";

    [ObservableProperty]
    private string? errorMessage;

    public bool CanUseEngineActions =>
        ConnectionStatus == ConnectionStatus.Connected
        && !string.IsNullOrWhiteSpace(BaseUrl)
        && !string.IsNullOrWhiteSpace(Token)
        && !IsAuthenticationFailed;

    public bool IsChecking => ConnectionStatus == ConnectionStatus.Connecting;

    public bool HasError => !string.IsNullOrWhiteSpace(ErrorMessage);
}
