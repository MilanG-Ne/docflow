'use client';
import { useState } from 'react';
import { ArrowRight, FileText, Layers, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';

export default function Home() {
  const [notice, setNotice] = useState('');
  return (
    <main className="entry">
      <section className="entry-brand">
        <a className="wordmark" href="/">
          <span className="brand-icon">
            <Layers size={22} />
          </span>
          docflow<span className="brand-dot">.</span>
        </a>
        <div className="entry-copy">
          <p className="eyebrow">ALDER & CO. / PROPOSAL WORKSPACE</p>
          <h1>
            Good work starts
            <br />
            with a clear proposal.
          </h1>
          <p>
            Bring the scope, fees, and review into one place. Every approval
            belongs to one exact revision.
          </p>
          <ol className="workflow">
            <li>
              <FileText />
              Write the proposal
            </li>
            <li>
              <Layers />
              Generate Word & PDF
            </li>
            <li>
              <ShieldCheck />
              Review and approve
            </li>
          </ol>
        </div>
        <p className="small">
          A fictional consultancy. A working document workflow.
        </p>
      </section>
      <section className="entry-form">
        <div className="login-panel">
          <p className="eyebrow">WELCOME TO DOCFLOW</p>
          <h2>Your proposals, in order.</h2>
          <p className="muted">
            Choose a demo account to explore both sides of the review process.
          </p>
          <Tabs defaultValue="author">
            <TabsList className="login-tabs">
              <TabsTrigger value="author">Author</TabsTrigger>
              <TabsTrigger value="reviewer">Reviewer</TabsTrigger>
            </TabsList>
            <TabsContent value="author">
              <div className="account-avatar">AN</div>
              <h3>Alex Novak</h3>
              <p className="muted">
                Prepare proposals, generate files, and send revisions for
                review.
              </p>
            </TabsContent>
            <TabsContent value="reviewer">
              <div className="account-avatar">JL</div>
              <h3>Jamie Lee</h3>
              <p className="muted">
                Review the scope and fees, leave feedback, and approve a
                revision.
              </p>
            </TabsContent>
          </Tabs>
          <Button
            className="login-button"
            onClick={() =>
              setNotice(
                'The document service is being connected. Check back shortly.',
              )
            }
          >
            Open workspace <ArrowRight />
          </Button>
          {notice && (
            <p role="status" className="notice">
              {notice}
            </p>
          )}
          <p className="small muted">
            Demo accounts use fictional information. Changes are saved in your
            local database.
          </p>
        </div>
      </section>
    </main>
  );
}
