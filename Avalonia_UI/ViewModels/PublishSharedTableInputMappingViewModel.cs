using Avalonia_UI.Localization;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class PublishSharedTableInputMappingViewModel : ViewModelBase
{
    private readonly ILocalizationService _localizationService;

    public PublishSharedTableInputMappingViewModel(
        int inputIndex,
        WorkflowDefinitionConnectionListItemViewModel? connection,
        string exportName,
        ILocalizationService localizationService)
    {
        InputIndex = inputIndex;
        Connection = connection;
        this.exportName = exportName;
        _localizationService = localizationService;
    }

    public int InputIndex { get; }

    public WorkflowDefinitionConnectionListItemViewModel? Connection { get; }

    public bool IsConnected => Connection is not null;

    public string InputText => Connection is null
        ? _localizationService.Format(
            "format.node_config.shared.unmapped_input",
            InputIndex)
        : _localizationService.Format(
            "format.node_config.shared.input_connection",
            InputIndex,
            Connection.SourceNodeId,
            Connection.SourcePort,
            Connection.TargetPort);

    [ObservableProperty]
    private string exportName = string.Empty;

    public void RefreshLocalizedText()
    {
        OnPropertyChanged(nameof(InputText));
    }
}
