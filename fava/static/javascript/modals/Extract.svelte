<script>
  import { saveEntries } from "../entries";
  import { _, fetchAPI } from "../helpers";
  import { urlHash, closeOverlay } from "../stores";

  import Balance from "../entry-forms/Balance.svelte";
  import Note from "../entry-forms/Note.svelte";
  import Transaction from "../entry-forms/Transaction.svelte";

  let entries = [];
  let component;
  let currentIndex = 0;
  let duplicate;
  let duplicates;
  let entry;
  let shown;

  function isDuplicate(e) {
    return !!e.meta.__duplicate__;
  }

  $: shown = $urlHash.startsWith("extract");
  $: if (shown) {
    fetchAPI("extract", $urlHash.slice(8)).then(data => {
      entries = data;
    });
  }
  $: entry = entries[currentIndex];
  $: if (entry) {
    component = { Balance, Note, Transaction }[entry.type];
    duplicates = entry && entries.filter(e => isDuplicate(e)).length;
    duplicate = isDuplicate(entry);
  }

  async function submitOrNext() {
    if (currentIndex < entries.length - 1) {
      currentIndex += 1;
    } else {
      await saveEntries(entries.filter(e => !isDuplicate(e)));
      closeOverlay();
    }
  }

  function previousEntry() {
    currentIndex = Math.max(currentIndex - 1, 0);
  }

  function toggleDuplicate() {
    entry.meta.__duplicate__ = !entry.meta.__duplicate__;
  }
</script>

<div class:shown class="overlay">
  <div class="overlay-background" on:click={closeOverlay} />
  <div class="overlay-content">
    <button type="button" class="muted close-overlay" on:click={closeOverlay}>
      x
    </button>
    <form novalidate={duplicate} on:submit|preventDefault={submitOrNext}>
      <h3>{_('Import')}</h3>
      {#if entry}
        <div class="headerline">
          <h3>
            Entry {currentIndex + 1} of {entries.length} ({entries.length - duplicates}
            to import):
          </h3>
          <span class="spacer" />
          <label class="button muted">
            <input
              type="checkbox"
              checked={duplicate}
              on:click={toggleDuplicate} />
            ignore duplicate
          </label>
        </div>
        <div class:duplicate class="ingest-row">
          <svelte:component this={component} bind:entry />
        </div>
        <div class="fieldset">
          {#if currentIndex > 0}
            <button
              type="button"
              class="muted"
              on:click={() => {
                currentIndex = 0;
              }}>
              ⏮
            </button>
            <button type="button" class="muted" on:click={previousEntry}>
              {_('Previous')}
            </button>
          {/if}
          <span class="spacer" />
          {#if currentIndex < entries.length - 1}
            <button type="submit">{_('Next')}</button>
            <button
              type="button"
              class="muted"
              on:click={() => {
                currentIndex = entries.length - 1;
              }}>
              ⏭
            </button>
          {:else}
            <button type="submit">{_('Save')}</button>
          {/if}
        </div>
        <hr />
        {#if entry.meta.__source__}
          <h3>
            {_('Source')}
            {#if entry.meta.lineno > 0}({_('Line')}: {entry.meta.lineno}){/if}
          </h3>
          <pre>{entry.meta.__source__}</pre>
        {/if}
      {/if}
    </form>
  </div>
</div>
