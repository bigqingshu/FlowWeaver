using System;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;

namespace Avalonia_UI.ViewModels;

public sealed class SharedPublicationCatalogEntryListItemViewModel
{
    public SharedPublicationCatalogEntryListItemViewModel(
        SharedPublicationCatalogEntryDto entry,
        DisplayTextFormatter? displayTextFormatter = null)
    {
        DisplayTextFormatter = displayTextFormatter ?? DisplayTextFormatter.Invariant;
        ShareName = entry.ShareName;
        LatestPublishedVersion = entry.LatestPublishedVersion;
        PublishedVersionCount = entry.PublishedVersionCount;
        LatestMemberCount = entry.LatestMemberCount;
        LatestCreatedAt = entry.LatestCreatedAt;
    }

    public string ShareName { get; }

    public int LatestPublishedVersion { get; }

    public int PublishedVersionCount { get; }

    public int LatestMemberCount { get; }

    public DateTimeOffset LatestCreatedAt { get; }

    public DisplayTextFormatter DisplayTextFormatter { get; }

    public string LatestVersionText => $"v{LatestPublishedVersion}";

    public string PublishedVersionCountText =>
        DisplayTextFormatter.FormatVersionCount(PublishedVersionCount);

    public string LatestMemberCountText =>
        DisplayTextFormatter.FormatMemberCount(LatestMemberCount);

    public string LatestCreatedAtText =>
        LatestCreatedAt.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss");
}
