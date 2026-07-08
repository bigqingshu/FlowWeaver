using Avalonia_UI.Api;
using Avalonia_UI.Services;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private readonly EngineHostHealthClient _healthClient;
    private readonly IConnectionSettingsStore _connectionSettingsStore;

    public string ConnectionBaseUrlText => T("connection.base_url");

    public string ConnectionTokenText => T("connection.token");

    public string ConnectionStatusText => T("connection.status");

    public string ConnectionEventsText => T("connection.events");

    public string CheckConnectionText => T("connection.check");

    public string StreamText => T("connection.stream");

    public string StopText => T("connection.stop");

}
