using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private static bool IsKnownShellPageKey(ShellPageKey key)
    {
        return BuiltinShellPages.All.Any(page => page.Key == key);
    }

    private bool IsKnownShellPageIndex(int index)
    {
        return index >= 0 && index < ShellNavigationItems.Count;
    }
}
