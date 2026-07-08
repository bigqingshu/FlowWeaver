using System;
using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private ShellNavigationItemViewModel GetShellNavigationItem(ShellPageKey key)
    {
        return ShellNavigationItems.FirstOrDefault(item => item.Key == key)
            ?? throw new InvalidOperationException($"Shell navigation item '{key}' was not found.");
    }

    private int GetShellNavigationItemIndex(ShellPageKey key)
    {
        for (var index = 0; index < ShellNavigationItems.Count; index++)
        {
            if (ShellNavigationItems[index].Key == key)
            {
                return index;
            }
        }

        throw new InvalidOperationException($"Shell navigation item '{key}' was not found.");
    }
}
