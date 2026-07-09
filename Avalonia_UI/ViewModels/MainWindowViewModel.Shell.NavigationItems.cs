using System.Collections.ObjectModel;
using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public ObservableCollection<ShellNavigationItemViewModel> ShellNavigationItems { get; } =
        new();

    public ShellNavigationItemViewModel WorkflowsNavigationItem =>
        GetShellNavigationItem(ShellPageKey.Workflows);

    public ShellNavigationItemViewModel DataPreviewNavigationItem =>
        GetShellNavigationItem(ShellPageKey.DataPreview);

    public ShellNavigationItemViewModel RunsNavigationItem =>
        GetShellNavigationItem(ShellPageKey.Runs);

    public ShellNavigationItemViewModel DataNavigationItem =>
        GetShellNavigationItem(ShellPageKey.Data);

    public ShellNavigationItemViewModel LogsNavigationItem =>
        GetShellNavigationItem(ShellPageKey.Logs);

    public ShellNavigationItemViewModel SettingsNavigationItem =>
        GetShellNavigationItem(ShellPageKey.Settings);

    public ShellNavigationItemViewModel SelectedShellNavigationItem =>
        GetShellNavigationItem(SelectedShellPageKey);

    public ShellPageContentKey SelectedShellPageContentKey =>
        SelectedShellNavigationItem.ContentKey;

    private void RefreshShellNavigationItems()
    {
        ShellNavigationItems.Clear();
        foreach (var descriptor in BuiltinShellPages.All.OrderBy(page => page.SortOrder))
        {
            ShellNavigationItems.Add(
                new ShellNavigationItemViewModel(
                    descriptor,
                    ResolveShellPageHeaderText(descriptor)));
        }

        SynchronizeSelectedShellPageIndex(SelectedShellPageKey);
        NotifyShellNavigationItemsChanged();
    }
}
