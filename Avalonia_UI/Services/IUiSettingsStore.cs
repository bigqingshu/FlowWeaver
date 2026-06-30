using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Models;

namespace Avalonia_UI.Services;

public interface IUiSettingsStore
{
    Task<PersistedUiSettings> LoadAsync(CancellationToken cancellationToken = default);

    Task SaveAsync(
        PersistedUiSettings settings,
        CancellationToken cancellationToken = default);
}
