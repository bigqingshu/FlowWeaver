using System.Threading.Tasks;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanRefreshNodeDefinitions()
    {
        return CanUseEngineActions && !IsLoadingNodeDefinitions;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshNodeDefinitions))]
    private async Task RefreshNodeDefinitionsAsync()
    {
        await RefreshNodeDefinitionsCoreAsync(allowStateCacheHit: false);
    }
}
