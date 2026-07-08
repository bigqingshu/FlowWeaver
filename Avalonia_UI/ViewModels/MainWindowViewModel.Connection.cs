using Avalonia_UI.Api;
using Avalonia_UI.Services;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private readonly EngineHostHealthClient _healthClient;
    private readonly IConnectionSettingsStore _connectionSettingsStore;
}
