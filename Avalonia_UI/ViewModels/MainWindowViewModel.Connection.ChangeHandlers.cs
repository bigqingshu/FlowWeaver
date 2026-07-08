using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnConnectionStatusChanged(ConnectionStatus value)
    {
        OnPropertyChanged(nameof(IsChecking));
        NotifyEngineActionStateChanged();
        CheckConnectionCommand.NotifyCanExecuteChanged();
    }

    partial void OnTokenChanged(string value)
    {
        IsAuthenticationFailed = false;
        InvalidateNodeDefinitionCatalogCacheState();
        NotifyEngineActionStateChanged();
    }

    partial void OnBaseUrlChanged(string value)
    {
        IsAuthenticationFailed = false;
        InvalidateNodeDefinitionCatalogCacheState();
        NotifyEngineActionStateChanged();
        CheckConnectionCommand.NotifyCanExecuteChanged();
        StartRuntimeEventStreamCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsRuntimeEventStreamConnectedChanged(bool value)
    {
        NotifyEngineActionStateChanged();
    }

    partial void OnIsAuthenticationFailedChanged(bool value)
    {
        NotifyEngineActionStateChanged();
    }

    partial void OnErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasError));
    }
}
