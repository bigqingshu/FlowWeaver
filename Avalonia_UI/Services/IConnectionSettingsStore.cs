using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Models;

namespace Avalonia_UI.Services;

public interface IConnectionSettingsStore
{
    Task<PersistedConnectionSettings> LoadAsync(CancellationToken cancellationToken = default);

    Task SaveAsync(
        PersistedConnectionSettings settings,
        CancellationToken cancellationToken = default);
}
