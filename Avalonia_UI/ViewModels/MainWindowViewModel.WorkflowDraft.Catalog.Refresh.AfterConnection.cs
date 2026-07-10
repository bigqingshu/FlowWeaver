using System.Threading.Tasks;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private async Task RefreshNodeDefinitionsAfterHealthyConnectionAsync()
    {
        if (!CanRefreshNodeDefinitions())
        {
            return;
        }

        await RefreshNodeDefinitionsCoreAsync(allowStateCacheHit: true);
    }
}
