using System;
using System.Threading;
using System.Threading.Tasks;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public async Task LoadUiSettingsAsync(
        CancellationToken cancellationToken = default)
    {
        try
        {
            var settings = await _uiSettingsStore.LoadAsync(cancellationToken);
            await ApplyThemeAsync(settings.ThemeVariant, save: false, cancellationToken);
            await ApplyLanguageAsync(settings.LanguageCode, save: false, cancellationToken);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception ex)
        {
            ErrorMessage = F("format.ui_settings_load_failed", ex.Message);
        }
    }
}
